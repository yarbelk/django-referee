from __future__ import unicode_literals

import logging

from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

from datetime_truncate import truncate_day


logger = logging.getLogger('referee')


class ParticipantBase(models.Model):
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


class LimitedParticipation(ParticipantBase):
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
        '''Record that the user got an extra chance.'''
        self.chances += 1
        self.extra_chances_received += 1

        if commit:
            self.save()


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
