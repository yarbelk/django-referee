import datetime

from django.test import TestCase
from django.utils import timezone

from mock import patch

from .factories import TimePeriodFactory, ParticipantFactory, PrizeFactory
from ..models import Participant, Prize, TimePeriodPrizeAvailable, Claim


class PrizeAndClaimTest(TestCase):
    def setUp(self):
        self.total_units = 3
        self.period = TimePeriodFactory.create()
        self.prize = PrizeFactory.create(time_periods=self.period,
                                       total_units=self.total_units)
        self.participant = ParticipantFactory.create(spin_times=100)
        self.participant2 = ParticipantFactory.create()

    def test_should_be_as_many_left_as_total_when_no_claimed(self):
        self.assertEqual(self.prize.units_left(self.period), self.prize.total_units)

    def test_unlimited_should_always_return_1_left(self):
        self.prize.total_units = -1
        self.prize.save()

        inf = float('Inf')

        self.assertEqual(self.prize.units_left(self.period), inf)
        self.prize.claim(self.period, self.participant)
        self.assertEqual(self.prize.units_left(self.period), inf)

    def test_prize_claim_for_user(self):
        self.assertEqual(Claim.objects.all().count(), 0)
        self.prize.claim(self.period, self.participant)
        self.assertEqual(Claim.objects.all().count(), 1)

    def test_can_claim_only_once_per_item_unless_unlimited(self):
        self.prize.claim(self.period, self.participant)
        self.assertRaises(Prize.AlreadyClaimed, self.prize.claim,
                          self.period, self.participant)

    def test_new_claim_should_have_unclaimed_at_set(self):
        now = timezone.utc.localize(datetime.datetime(2013, 7, 1))
        later = now + datetime.timedelta(minutes=Claim.MINUTES_UNTIL_UNCLAIMED)
        with patch.object(timezone, 'now', return_value=now):
            claim = self.prize.claim(self.period, self.participant)

        self.assertEqual(claim.unclaimed_at, later)

    def test_new_claim_should_not_have_claim_confirmed(self):
        claim = self.prize.claim(self.period, self.participant)
        self.assertFalse(claim.claim_confirmed)

    def test_when_claim_is_confirmed_claim_confirmed_at_should_be_set(self):
        claim = self.prize.claim(self.period, self.participant)
        confirmed_at = claim.claim_confirmed_at
        self.assertTrue(confirmed_at is None)

        claim.confirm()
        self.assertTrue(claim.claim_confirmed)
        self.assertNotEqual(confirmed_at, claim.claim_confirmed_at)

    def test_should_have_one_less_left_when_claimed(self):
        self.prize.claim(self.period, self.participant)
        self.assertEqual(self.prize.units_left(self.period), self.total_units - 1)

    def test_should_not_be_able_to_claim_more_than_total_units(self):
        self.prize.total_units = 1
        self.prize.save()
        self.prize.claim(self.period, self.participant)

        self.assertRaises(Prize.AllClaimed, self.prize.claim,
                          self.period, self.participant)

    def test_if_claim_not_confirmed_within_x_minutes_claim_is_lost(self):
        now = timezone.utc.localize(datetime.datetime(2013, 7, 1))
        with patch.object(timezone, 'now', return_value=now):
            self.prize.claim(self.period, self.participant)
            self.assertEqual(self.prize.units_left(self.period), self.total_units - 1)

        with patch.object(timezone, 'now',
                          return_value=(
                              now + datetime.timedelta(
                                  minutes=Claim.MINUTES_UNTIL_UNCLAIMED + 1
                              ))):
            self.assertEqual(self.prize.units_left(self.period), self.total_units)

    def test_if_claim_confirmed_within_x_minutes_claim_is_kept(self):
        now = timezone.utc.localize(datetime.datetime(2013, 7, 1))
        with patch.object(timezone, 'now', return_value=now):
            claim = self.prize.claim(self.period, self.participant)
            self.assertEqual(self.prize.units_left(self.period), self.total_units - 1)
            claim.confirm()

        with patch.object(timezone, 'now',
                          return_value=(
                              now + datetime.timedelta(
                                  minutes=Claim.MINUTES_UNTIL_UNCLAIMED + 1
                              ))):
            self.assertEqual(self.prize.units_left(self.period), self.total_units - 1)

    def test_confirm_claim_should_be_able_to_set_questions(self):
        claim = self.prize.claim(self.period, self.participant)
        q1, q3 = 'whatever d00d', 'nuhuuu'
        claim.confirm(dict(question1=q1, question3=q3))
        self.assertEqual(claim.question1, q1)
        self.assertEqual(claim.question3, q3)

    def test_dont_set_all_claimed_when_all_claimed_but_not_confirmed(self):
        now = timezone.utc.localize(datetime.datetime(2013, 7, 1))
        prize = PrizeFactory.create(time_periods=self.period, total_units=1)
        with patch.object(timezone, 'now', return_value=now):
            prize.claim(self.period, self.participant)
            self.assertEqual(prize.units_left(self.period), 0)

        with patch.object(timezone, 'now',
                          return_value=(
                              now + datetime.timedelta(
                                  minutes=Claim.MINUTES_UNTIL_UNCLAIMED - 1
                              ))):
            self.assertRaises(Prize.AllClaimed, prize.claim,
                              self.period, self.participant)
            prize = Prize.objects.get(pk=prize.pk)
            self.assertFalse(prize.time_period_claimed.get(time_period=self.period).all_claimed)

    def test_set_all_claimed_when_all_claimed_but_not_confirmed(self):
        '''When all products has been confirmed and none hasn't been
        fully claimed, mark it as all claimed.
        '''
        now = timezone.utc.localize(datetime.datetime(2013, 7, 1))
        prize = PrizeFactory.create(time_periods=self.period, total_units=1)
        with patch.object(timezone, 'now', return_value=now):
            claim = prize.claim(self.period, self.participant)
            claim.confirm()
            self.assertEqual(prize.units_left(self.period), 0)

        with patch.object(timezone, 'now',
                          return_value=(
                              now + datetime.timedelta(
                                  minutes=Claim.MINUTES_UNTIL_UNCLAIMED - 1
                              ))):
            self.assertRaises(Prize.AllClaimed, prize.claim,
                              self.period, self.participant)
            prize = Prize.objects.get(pk=prize.pk)
            self.assertTrue(prize.all_claimed)


class RandomPrize(TestCase):
    def setUp(self):
        self.total_units = 1
        self.period = TimePeriodFactory.create()
        self.prize = PrizeFactory.create_batch(5, time_periods=self.period,
                                             total_units=self.total_units)
        self.participant = ParticipantFactory.create()
        self.participant2 = ParticipantFactory.create()

    def test_get_random_prize(self):
        prize = Prize.get_random(self.period)
        self.assertTrue(prize.pk)

    def test_cant_get_random_when_no_units_left(self):
        TimePeriodPrizeAvailable.objects.all().update(all_claimed=True)
        self.assertRaises(Prize.AllClaimed, Prize.get_random, self.period)

    def test_can_get_item_that_has_all_claimed_but_not_claim_it(self):
        TimePeriodPrizeAvailable.objects.all().update(all_claimed=True)
        prize = Prize.objects.all()[0]
        prize_timeperiod = TimePeriodPrizeAvailable.objects.get(
            prize=prize,
            time_period=self.period
        )
        prize_timeperiod.all_claimed = False
        prize_timeperiod.save()

        prize.claim(self.period, self.participant)

        random_prize = Prize.get_random(self.period)
        self.assertEqual(random_prize.pk, prize.pk)
        self.assertRaises(Prize.AllClaimed, random_prize.claim,
                          self.period, self.participant2)

    def test_get_only_random_unlimited(self):
        unlimited = Prize.objects.all().order_by('?')[0]
        unlimited.total_units = -1
        unlimited.save()

        prize = Prize.get_random_unlimited(self.period)
        self.assertEqual(prize.pk, unlimited.pk)

    def test_get_and_claim_should_return_prize_and_claim(self):
        prize, claim = Prize.get_and_claim_random(self.period, self.participant)
        Prize.objects.get(pk=prize.pk)
        Claim.objects.get(pk=claim.pk)


class ClaimTimePeriod(TestCase):
    def setUp(self):
        self.total_units = 1
        self.period = TimePeriodFactory.create()
        self.period2 = TimePeriodFactory.create()
        self.prize = PrizeFactory.create(time_periods=[self.period, self.period2],
                                       total_units=1)

        self.participant = ParticipantFactory.create()
        self.participant2 = ParticipantFactory.create()

    def test_claim_from_two_periods_without_problems(self):
        '''These two claims for two different users for the same item
        in different periods should both work without any exceptions
        raised.
        '''
        claim1 = self.prize.claim(self.period, self.participant)
        claim2 = self.prize.claim(self.period2, self.participant2)
        self.assertTrue(claim1.pk)
        self.assertTrue(claim2.pk)

    def test_user_cant_claim_same_item_over_two_periods(self):
        self.prize.claim(self.period, self.participant)
        self.assertRaises(Prize.AlreadyClaimed, self.prize.claim,
                          self.period2, self.participant)
