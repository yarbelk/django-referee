# flake8:noqa
from .time_period import TimePeriodBase
from .participant import (
    ParticipantBase,
    LimitedParticipation,
    ExtraChanceDaily,
)
from .prize import (
    PrizeBase,
    PrizeUniqueClaim,
    PrizeClaimUsesChance,
    PrizeConfirmClaim,

    ClaimBase,
    ClaimNeedsConfirmation,

    TimePeriodPrizeAvailableBase
)


class Participant(ParticipantBase):
    pass


class TimePeriod(TimePeriodBase):
    pass


class Prize(PrizeBase):
    pass


class Claim(ClaimBase):
    pass


class TimePeriodPrizeAvailable(TimePeriodPrizeAvailableBase):
    pass
