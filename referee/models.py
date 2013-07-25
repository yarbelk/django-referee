from __future__ import unicode_literals

import logging

from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

from datetime_truncate import truncate_day

from .managers import CurrentTimePeriodManager, CurrentAndPastTimePeriodManager


logger = logging.getLogger('referee')


class TimePeriod(models.Model):
    objects = models.Manager()
    current = CurrentTimePeriodManager()
    current_and_past = CurrentAndPastTimePeriodManager()
    name = models.CharField(max_length=100, blank=False, unique=True,
                            help_text=_('The name of this time period'))
    period_start = models.DateTimeField(blank=False, null=False)
    period_end = models.DateTimeField(blank=False, null=True)

    class Meta:
        unique_together = ('period_start', 'period_end',)
        ordering = ('-period_start',)

    def __unicode__(self):
        return self.name

    def clean(self, *args, **kwargs):
        super(TimePeriod, self).clean(*args, **kwargs)
        cls = self.__class__

        if self.period_end <= self.period_start:
            raise ValidationError(
                _('period_end needs to be after period_start')
            )

        # Don't overlap single dates with another period
        for period in ('period_start', 'period_end'):
            datetime_ = getattr(self, period)
            q = cls.objects.extra(
                where=['%s BETWEEN period_start AND period_end'],
                params=[datetime_]
            )
            if self.pk: q = q.exclude(pk=self.pk)

            if q.exists():
                raise ValidationError(
                    _('{0} already in another period.'.format(period))
                )

        # A period shall not encompass his neighbours period
        q = cls.objects.extra(
            where=['((period_start BETWEEN %s AND %s) '
                   ' OR (period_end BETWEEN %s AND %s))'],
            params=[self.period_start, self.period_end,
                    self.period_start, self.period_end]
        )
        if self.pk: q = q.exclude(pk=self.pk)

        if(q.exists()):
            raise ValidationError(_('This period encompass another period.'))

    @classmethod
    def past_periods(cls):
        try:
            current = cls.current.get().period_start
        except cls.DoesNotExist:
            # When there is no current time periods at all, just
            # anything before now
            current = timezone.now()

        return cls.objects.filter(period_start__lt=current)


class BasicParticipant(models.Model):
    '''This model sliced out of a daily lucky wheel app.

    Reusable model usage to look something like:

    > p = Participant.objects.get(pk=1)
    # Defaults to has_personal_particulars, can be added to include
    # other tests
    > p.can_participate
    True
    > p.has_personal_particulars
    True
    > p.chances # If a game of luck, how many chances does this user have
    > p.add_more_chances(n)

    A participant is used together with a time period on a Prize to be claimed.
    '''
    user = models.OneToOneField(User, related_name="+")
    full_name = models.CharField(max_length=60)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=50)

    class Meta:
        abstract = True

    @property
    def has_personal_particulars(self):
        '''Has the user entered all the personal particulars required?'''
        return bool(len(self.full_name) and len(self.phone)
                    and len(self.email))

    def set_particulars(self, data):
        changed = False
        for attr in ('full_name', 'phone', 'email'):
            val = data.get(attr)
            if val and getattr(self, attr) != val:
                setattr(self, attr, val)
                changed = True

        if changed: self.save()

        return self

    def __unicode__(self):
        self.full_name


class LimitedParticipation(models.Model):
    '''Sometimes a competition/giveaway only allows a user to enter X
    amounts of times. Or to claim Y amount of prizes. Or maybe they can
    enter once a day.
    '''
    class NoMoreChances(IntegrityError):
        '''Raised when the limited amount has run out for the user. Does not
        necessarily mean the user can't _ever_ enter again.
        '''

    finish_quiz = models.BooleanField(default=False)
    chances = models.PositiveIntegerField(
        default=1,
        help_text=_('The amount of times the user currently can participate')
    )
    last_chance_used_at = models.DateTimeField(null=True, blank=True)
    extra_chances_received = models.PositiveIntegerField(
        default=0,
        help_text=_('If the user has received extra chances for any reason. '
                    'Just informative.'),
        editable=False,
    )

    class Meta:
        abstract = True

    @property
    def has_chances(self):
        return self.chances > 0

    def use_chance(self, commit=True):
        if not self.has_chances:
            raise self.NoMoreChances()
        elif self.chance > 0:
            self.chances -= 1
        else:
            msg = '`has_chances` is true but chance is not > 0'
            logger.error(msg, extra={
                'has_chances': self.has_chances,
                'chances': self.chances,
            })
            raise ValueError(msg)

        self._set_last_chance_used()

        if commit:
            self.save()

    def _set_last_chance_used(self):
        '''So that this can be used for changing the way extra chances are
        given based on the time. If the user receives a new chance
        every 5 minutes and more than 5 minutes has past since the
        very last chance was used, then give the user a new chance.
        '''
        self.last_chance_used_at = timezone.now()

    def receive_extra_chance(self, commit=True):
        self.chances += 1
        self.extra_chances_received += 1
        self.extra_chance_received_hook()

        if commit:
            self.save()

    def extra_chance_received_hook(self):
        '''If any extra logic should be performed when an extra chance has
        been received then add it here. Will be run before the model is
        saved.
        '''


class ExtraChanceDaily(LimitedParticipation):
    '''Allows the particpant to receive an extra chance at the stroke of
    midnight for every day past the first day.

    One assumption is that the very first chance will be received from
    the participant, and as such an empty `last_chance_used_at` will
    not receive an extra chance.

    Any extra chances received from time bonuses will not be
    registered in `extra_chances_received`.

    To set it to receive one extra chance more often override
    `_last_new_period` and every time `last_chance_used_at` is before
    that timestamp a new chance will be awarded.

    '''
    class Meta:
        abstract = True

    @property
    def has_chances(self):
        return self.chances > 0 or self.extra_chance_from_time

    @property
    def extra_chance_from_time(self):
        '''Should the participant receive an extra chance because he got an
        extra chance lying about?
        '''
        return (self.last_chance_used_at
                and self.last_chance_used_at >= self._last_new_period)

    def _last_new_period(self):
        '''The time `last_chance_used_at` must be prior to receive an extra
        chance
        '''
        return truncate_day(timezone.now())

    def _set_last_chance_used(self):
        '''If `last_chance_used_at` has never been set then there's no extra
         chances to be had. The chance already came with the default
         Participant.
        '''
        if(self.chances == 0
           and (not self.last_chance_used_at or self.extra_chance_from_time)):
            self.last_chance_used_at = timezone.now()


class PrizeBase(models.Model):
    '''A prize is something that a participant can win/receive during a
    contest.  A prize can be unlimited if the total_units available is
    -1, otherwise limited.  When all of a prize has been claimed then
    `AllClaimed` will be raised.  If the Prize can only be claimed
    once per participant then `AlreadyClaimed` will be raised.

    A prize can be randomly assigned to a user or a specific one can
    be claimed.
    '''
    class AllClaimed(IntegrityError): pass

    RANDOM_MAX_TRY = 6
    '''How many times `get_and_claim_random` will try before it gives
    up and returns `get_random_unlimited`
    '''

    time_periods = models.ManyToManyField(TimePeriod, related_name='prizes',
                                          through='TimePeriodPrizeAvailable')
    total_units = models.IntegerField(
        default=3,
        help_text=_('-1 means unlimited. Units available per time period')
    )
    description = models.CharField(max_length=255)

    def __unicode__(self):
        return self.description

    def units_left(self, time_period):
        '''Returns number of units left to be claimed. If unit has
        unlimited value is `Inf`.
        '''
        if self.total_units == -1:
            return float('Inf')
        else:
            return self.total_units - (
                self.claimed.filter(time_period=time_period).count()
            )

    @property
    def claimed(self):
        '''A queryset for all gifts that has been successfully claimed'''
        return (Claim.objects
                .filter(prize=self)
                .exclude(unclaimed_at__lt=timezone.now(),
                         claim_confirmed=False))

    def all_claimed(self, period):
        return self.time_period_won.get(time_period=period).all_claimed

    @property
    def is_unlimited(self):
        return self.total_units == -1

    def claim(self, time_period, particpant):
        if self.all_claimed(time_period):
            pass
        elif self.units_left(time_period):
            self._units_left_before_claim_hook(time_period, particpant)

            participant.use_chance()
            claim = Claim.objects.create(prize=self,
                                         participant=participant,
                                         time_period=time_period)
            self._after_successfull_claim_hook(claim)

            return claim
        else:
            # When there are no units left and prize not marked as all claimed
            # see if there's any left that:
            # - hasn't been confirmed
            # - and hasn't expired
            #
            # If all has been either confirmed or expired then mark
            # prize as `all_claimed`.
            if(self.all_claims
               .filter(unclaimed_at__gt=timezone.now,
                       claim_confirmed=False).count() == 0):
                (self.time_period_claimed
                 .get(time_period=time_period)
                 .set_all_claimed())

        raise self.AllClaimed(
            _('All {0} of this gift has been claimed'.format(
                self.total_units
            )))

    def _units_left_before_claim_hook(self, time_period, participant):
        '''Hook to allow adding extra logic if there's any units left.  Should
        raise an exception if there's any issues with the participant
        claiming the prize.

        '''

    def _after_successfull_claim_hook(claim):
        '''After a new claim objects has been created'''

    @classmethod
    def get_random(cls, time_period):
        '''Receive a random price that still has units left'''
        # This might not be the best way of doing random, do some
        # benchmarking
        prize = (cls.objects
                 .filter(time_period_claimed__time_period=time_period,
                         time_period_claimed__all_claimed=False)
                 .order_by('?'))

        if prize:
            return prize[0]
        else:
            raise cls.AllClaimed(_('All prizes has been claimed'))

    @classmethod
    def get_random_unlimited(cls, time_period):
        prize = (cls.objects
                 .filter(time_period_claimed__time_period=time_period,
                         time_period_claimed__all_claimed=False,
                         total_units=-1)
                 .order_by('?'))

        if prize:
            return prize[0]
        else:
            # This shouldn't happen.
            raise cls.AllClaimed(_('All unlimited prizes has been claimed'))

    @classmethod
    def get_and_claim_random(cls, time_period, participant):
        for i in range(0, cls.RANDOM_MAX_TRY):
            try:
                prize = cls.get_random(time_period)
                return prize, prize.claim(time_period, participant)
            except cls.AllClaimed:
                pass
            except cls.AlreadyClaimed:
                pass

        gift = cls.get_random_unlimited(time_period)
        return gift, gift.claim(time_period, participant)


class PrizeUniqueClaim(PrizeBase):
    class AlreadyClaimed(IntegrityError): pass

    CanReclaimUnlimited = True
    '''Can a participant claim an unlimited prize several times?'''

    def _units_left_before_claim_hook(self, time_period, participant):
        if Claim.objects.filter(prize=self,
                                participant=participant).exists():
            if not (self.is_unlimited and self.CanReclaimUnlimited):
                raise self.AlreadyClaimed(_('This prize has already been '
                                            'claimed by this participant'))


class PrizeConfirmClaim(PrizeBase):
    pass


class Claim(models.Model):
    MINUTES_UNTIL_UNCLAIMED = 5

    prize = models.ForeignKey(Prize, related_name='all_claims')
    participant = models.ForeignKey(Participant, related_name='claimed')
    time_period = models.ForeignKey(TimePeriod, related_name='+')
    claim_confirmed = models.BooleanField(
        default=False,
        help_text=_('If the participant has submitted the form')
    )
    claim_confirmed_at = models.DateTimeField(null=True)

    question1 = models.CharField(max_length=255, blank=True)
    question2 = models.CharField(max_length=255, blank=True)
    question3 = models.CharField(max_length=255, blank=True)
    question4 = models.CharField(max_length=255, blank=True)

    unclaimed_at = models.DateTimeField(
        editable=False,
        help_text=("If the claim hasn't been confirmed by this time, "
                   "it'll be forfeit"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def confirm(self, question_data=None):
        if question_data:
            for attr in ('question1', 'question2', 'question3', 'question4'):
                val = question_data.get(attr)
                if val:
                    setattr(self, attr, val)

        self.claim_confirmed = True
        self.claim_confirmed_at = timezone.now()
        self.save()

        return self

    def save(self, *args, **kwargs):
        if not self.pk:
            self.unclaimed_at = timezone.now() + datetime.timedelta(
                minutes=self.MINUTES_UNTIL_UNCLAIMED
            )

        return super(Claim, self).save(*args, **kwargs)


class TimePeriodPrizeAvailable(models.Model):
    time_period = models.ForeignKey(TimePeriod, related_name='+')
    prize = models.ForeignKey(Prize, related_name='time_period_claimed')
    all_claimed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('time_period', 'prize')

    def set_all_claimed(self, commit=True):
        self.all_claimed = True

        if commit:
            self.save()
