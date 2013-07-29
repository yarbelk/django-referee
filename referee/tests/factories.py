from datetime import datetime

from django.utils import timezone

import factory
from django_libs.tests.factories import UserFactory

from test_app.models import (Participant, Prize, TimePeriod,
                             TimePeriodPrizeAvailable)


class TimePeriodFactory(factory.DjangoModelFactory):
    FACTORY_FOR = TimePeriod

    name = factory.Sequence(lambda n: 'Period {0}'.format(n))
    period_start = factory.Iterator((
        datetime(2013, 5, 6, tzinfo=timezone.utc),
        datetime(2013, 5, 13, tzinfo=timezone.utc),
        datetime(2013, 5, 20, tzinfo=timezone.utc),
        datetime(2013, 5, 27, tzinfo=timezone.utc),
    ))
    period_end = factory.Iterator((
        datetime(2013, 5, 12, 23, 59, 59, tzinfo=timezone.utc),
        datetime(2013, 5, 19, 23, 59, 59, tzinfo=timezone.utc),
        datetime(2013, 5, 26, 23, 59, 59, tzinfo=timezone.utc),
        datetime(2013, 6, 2, 23, 59, 59, tzinfo=timezone.utc),
    ))


class ParticipantFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Participant
    user = factory.SubFactory(UserFactory)


class PrizeFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Prize

    total_units = 3
    description = factory.Sequence(lambda n: 'Prize {0}'.format(n))

    @factory.post_generation
    def time_periods(self, create, extracted, **kwargs):
        if extracted:
            try:
                for period in extracted:
                    TimePeriodPrizeAvailable.objects.create(time_period=period,
                                                            prize=self)
            except TypeError:
                TimePeriodPrizeAvailable.objects.create(time_period=extracted,
                                                        prize=self)
        else:
            TimePeriodPrizeAvailable.objects.create(
                time_period=TimePeriodFactory.create(),
                prize=self
            )
