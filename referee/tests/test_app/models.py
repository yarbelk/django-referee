from referee.models import (ClaimBase, ParticipantBase, PrizeBase,
                            TimePeriodBase, TimePeriodPrizeAvailableBase)


class Claim(ClaimBase):
    pass


class Participant(ParticipantBase):
    pass


class Prize(PrizeBase):
    pass


class TimePeriod(TimePeriodBase):
    pass


class TimePeriodPrizeAvailable(TimePeriodPrizeAvailableBase):
    pass
