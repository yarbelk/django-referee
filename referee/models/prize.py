from __future__ import unicode_literals

import datetime

from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class ClaimClassResolution(object):
    '''To fix object resolution dynamically add a class based off of the
    current models app label
    '''
    _ClaimClass = None
    @property
    def ClaimClass(self):
        if self._ClaimClass is None:
            self._ClaimClass = models.get_model(self._meta.app_label, 'Claim')

        return self._ClaimClass


class PrizeBase(ClaimClassResolution, models.Model):
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

    time_periods = models.ManyToManyField('TimePeriod', related_name='prizes',
                                          through='TimePeriodPrizeAvailable')
    total_units = models.IntegerField(
        default=3,
        help_text=_('-1 means unlimited. Units available per time period')
    )
    description = models.CharField(max_length=255)

    class Meta:
        abstract = True

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
        return (self.ClaimClass.objects
                .filter(prize=self)
                .exclude(unclaimed_at__lt=timezone.now(),
                         claim_confirmed=False))

    def all_claimed(self, period):
        return self.time_period_claimed.get(time_period=period).all_claimed

    @property
    def is_unlimited(self):
        return self.total_units == -1

    def claim(self, time_period, participant):
        '''Check that there is any units left and then claim 'em'''
        if self.all_claimed(time_period):
            pass  # Don't do book keeping since that's already done
        elif self.units_left(time_period) == 0:
            self.no_units_left_to_claim(time_period, participant)
        else:
            return self.create_claim(time_period, participant)

        raise self.AllClaimed(
            'All {0} of this gift has been claimed'.format(
                self.total_units
            ))

    def create_claim(self, time_period, participant):
        '''The actions tkane when the participant claims a prize'''
        # Not happy about the name for this method, any other options?
        # Thinking is that it should function like `form_valid` and
        # `form_invalid` in the normal CBVs...
        return self.ClaimClass.objects.create(prize=self,
                                              participant=participant,
                                              time_period=time_period)

    def no_units_left_to_claim(self, time_period, participant):
        '''Bookeeping to run when the prize hasn't been marked as all claimed
        but there are no units left to claim.
        '''
        self.set_all_claimed(time_period)

    def set_all_claimed(self, time_period):
        self.time_period_claimed.get(
            time_period=time_period
        ).set_all_claimed()

    @classmethod
    def get_random(cls, time_period):
        '''Receive a random price that still has units left'''
        # TODO: This might not be the best way of doing random, do
        # some benchmarking
        prize = (cls.objects
                 .filter(time_period_claimed__time_period=time_period,
                         time_period_claimed__all_claimed=False)
                 .order_by('?'))

        if prize:
            return prize[0]
        else:
            raise cls.AllClaimed('All prizes has been claimed')

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
            raise cls.AllClaimed('All unlimited prizes has been claimed')

    @classmethod
    def get_and_claim_random(cls, time_period, participant):
        for i in range(0, cls.RANDOM_MAX_TRY):
            try:
                prize = cls.get_random(time_period)
                return prize, prize.claim(time_period, participant)
            except cls.AllClaimed:
                pass
            # TODO Fix this in a nice, not very duplicate way
            #except cls.AlreadyClaimed:
            #    pass

        gift = cls.get_random_unlimited(time_period)
        return gift, gift.claim(time_period, participant)


class PrizeUniqueClaim(PrizeBase):
    class Meta:
        abstract = True

    class AlreadyClaimed(IntegrityError): pass

    CanReclaimUnlimited = True
    '''Can a participant claim an unlimited prize several times?'''

    def _units_left_before_claim_hook(self, time_period, participant):
        if self.ClaimClass.objects.filter(prize=self,
                                          participant=participant).exists():
            if not (self.is_unlimited and self.CanReclaimUnlimited):
                raise self.AlreadyClaimed('This prize has already been '
                                          'claimed by this participant')


class PrizeClaimUsesChance(PrizeBase):
    class Meta:
        abstract = True

    def create_claim(self, time_period, participant):
        '''If you're using chances for your participants you need to use them
        when they claim.
        '''
        participant.use_chance()
        return (super(PrizeClaimUsesChance, self)
                .allowed_to_claim(time_period, participant))


class PrizeConfirmClaim(PrizeBase):
    # TODO: Better naming for class?

    class Meta:
        abstract = True

    def no_units_left_to_claim(self, time_period, participant):
        # When there are no units left and prize not marked as all claimed
        # see if there's any left that:
        #
        # - hasn't been confirmed
        # - and hasn't expired
        #
        # If all has been either confirmed or expired then mark
        # prize as `all_claimed` for the `time_period`.
        if(self.all_claims
           .filter(unclaimed_at__gt=timezone.now,
                   claim_confirmed=False).count() == 0):
            return(super(PrizeConfirmClaim, self)
                   .no_units_left_to_claim(time_period, participant))


class ClaimBase(models.Model):
    prize = models.ForeignKey('Prize', related_name='all_claims')
    participant = models.ForeignKey('Participant', related_name='claimed')
    time_period = models.ForeignKey('TimePeriod', related_name='+')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ClaimNeedsConfirmation(ClaimBase):
    '''If a participant needs to confirm a claim. Imagine for instance a
    giveaway where the participant picks an item he/she wants and then
    needs to save an input form. Then set aside the prize for
    `MINUTES_UNTIL_UNCLAIMED` minutes and if no confirmation has
    gotten in by then release the prize back into the pool of
    available prizes.
    '''
    MINUTES_UNTIL_UNCLAIMED = 5
    '''How many minutes the participant has to confirm a claim'''

    claim_confirmed = models.BooleanField(default=False)
    claim_confirmed_at = models.DateTimeField(null=True)
    unclaimed_at = models.DateTimeField(
        editable=False,
        help_text=_("If the claim hasn't been confirmed by this time, "
                    "then it'll be forfeit"),
    )

    class Meta:
        abstract = True

    def confirm(self, commit=True):
        self.claim_confirmed = True
        self.claim_confirmed_at = timezone.now()

        if commit:
            self.save()

        return self

    def save(self, *args, **kwargs):
        if not self.pk:
            self.unclaimed_at = timezone.now() + datetime.timedelta(
                minutes=self.MINUTES_UNTIL_UNCLAIMED
            )

        return super(ClaimNeedsConfirmation, self).save(*args, **kwargs)


class TimePeriodPrizeAvailableBase(models.Model):
    '''A ManyToMany through model. Used mainly to keep track of if all
    prizes has been claimed.
    '''
    time_period = models.ForeignKey('TimePeriod', related_name='+')
    prize = models.ForeignKey('Prize', related_name='time_period_claimed')
    all_claimed = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = ('time_period', 'prize')

    def set_all_claimed(self, commit=True):
        self.all_claimed = True

        if commit:
            self.save()
