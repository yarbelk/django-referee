from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .managers import CurrentTimePeriodManager, CurrentAndPastTimePeriodManager


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


class Participant(models.Model):
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
    class NoMoreChances(IntegrityError): pass

    user = models.OneToOneField('auth.User', related_name="+")
    finish_quiz = models.BooleanField(default=False)
    spin_times = models.PositiveIntegerField(default=1)
    last_spin = models.DateTimeField(null=True, blank=True)
    extra_spins_received = models.PositiveIntegerField(default=0)

    full_name = models.CharField(max_length=60)
    nric = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=50)

    @property
    def has_personal_particulars(self):
        return (len(self.full_name) and len(self.nric)
                and len(self.phone) and len(self.email))

    def set_particulars(self, data):
        changed = False
        for attr in ('full_name', 'nric', 'phone', 'email'):
            val = data.get(attr)
            if val and getattr(self, attr) != val:
                setattr(self, attr, val)
                changed = True

        if changed: self.save()

        return self

    @property
    def can_spin(self):
        return not (self.spin_times <= 0
                    and (self.last_spin
                         and self.last_spin.date() == timezone.now().date()))

    def spin(self):
        if not self.can_spin:
            raise self.NoMoreSpins()
        elif self.spin_times > 0:
            self.spin_times -= 1

        # Urk logic
        if self.spin_times == 0:
            self.last_spin = timezone.now()

        self.save()

    def friend_accepted_invitation(self):
        self.spin_times += 1
        self.extra_spins_received += 1
        self.save()

    @property
    def friends_accepted_invitations(self):
        fb_user = self.user.get_profile().facebook
        return (FacebookInvitation.objects
                .filter(sender=fb_user)
                .exclude(accepted=None))

    def __unicode__(self):
        fb_user = self.user.get_profile().facebook
        if fb_user:
            return fb_user.full_name()
        else:
            return 'N/A'


class Prize(models.Model):
    '''A prize is something that a participant can win/receive during a
    contest.  A prize can be unlimited if the total_units available is
    -1, otherwise limited.  When all of a prize has been claimed then
    `AllClaimed` will be raised.  If the Prize can only be claimed
    once per participant then `AlreadyClaimed` will be raised.

    A prize can be randomly assigned to a user or a specific one can
    be claimed.
    '''
    class AllClaimed(IntegrityError): pass
    class AlreadyClaimed(IntegrityError): pass

    RANDOM_MAX_TRY = 6
    '''How many times `get_and_claim_random` will try before it gives
    up and returns `get_random_unlimited`
    '''

    time_periods = models.ManyToManyField(TimePeriod, related_name='prizes',
                                          through='TimePeriodPrizeAvailable')
    total_units = models.IntegerField(
        default=3,
        help_text=_('-1 unlimited. Units per time period')
    )
    description = models.CharField(max_length=255)
    slice_no = models.PositiveIntegerField(
        help_text=_('Corresponding slice in the wheel')
    )
    css_class = models.CharField(
        max_length=15,
        help_text=_('Used for displaying the image on the claim page')
    )

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
    def unlimited(self):
        return self.total_units == -1

    def claim(self, time_period, fan):
        if self.units_left(time_period):
            if(not self.unlimited
               and Claim.objects.filter(prize=self,
                                        participant=participant).exists()):
                raise self.AlreadyClaimed(
                    _('This gift has already been claimed by this user')
                )

            try:
                fan.spin()
            except Participant.NoMoreChances:
                raise
            else:
                return Claim.objects.create(prize=self,
                                            participant=participant,
                                            time_period=time_period)
        else:
            # When there are no units left and gift not marked as all claimed
            # see if there's any left that:
            # - hasn't been confirmed
            # - hasn't expired
            #
            # If not mark gift as `all_claimed`.
            if self.all_claimed(time_period):
                if(self.all_claims
                   .filter(unclaimed_at__gt=timezone.now,
                           claim_confirmed=False).count() == 0):
                    self.time_period_won.all_claimed = True
                    self.save()

            raise self.AllClaimed(
                _('All {0} of this gift has been claimed'.format(
                    self.total_units
                )))

    @classmethod
    def get_random(cls, time_period):
        '''This might not be the best way of doing random, do some
        benchmarking'''
        gift = (cls.objects
                .filter(time_period_won__time_period=time_period,
                        time_period_won__all_claimed=False)
                .order_by('?'))

        if gift:
            return gift[0]
        else:
            raise cls.AllClaimed(_('All gifts has been claimed'))

    @classmethod
    def get_random_unlimited(cls, time_period):
        prize = (cls.objects
                 .filter(time_period_won__time_period=time_period,
                         time_period_won__all_claimed=False,
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
    prize = models.ForeignKey(Prize, related_name='time_period_won')
    all_claimed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('time_period', 'prize')
