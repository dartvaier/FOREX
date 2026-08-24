"""
Formal Development / Validation / Out-of-Sample period definitions
for F8 (Robustness & Validation).

Roadmap §74 requires the final OOS period to act as a LOCKBOX: it must
not be consulted repeatedly during development. These definitions are
pre-registered constants (decided BEFORE looking at results) and the
lockbox guard is mechanical: running the OOS period through the sweep
harness requires an explicit --allow-oos flag.

Period roles (roadmap §78 DoD):

    DEVELOPMENT   2015-01-01 .. 2021-01-01   (subperiods 1-2)
    VALIDATION    2021-01-01 .. 2024-01-01   (subperiod 3)
    OOS (lockbox) 2024-01-01 .. 2027-01-01   (subperiod 4, most recent)

Contiguity: DEVELOPMENT.end == VALIDATION.start and
VALIDATION.end == OOS.start, covering the full dataset in order.
"""

from __future__ import annotations

from dataclasses import dataclass

DEVELOPMENT_DATE_FROM = "2015-01-01"
DEVELOPMENT_DATE_TO = "2021-01-01"

VALIDATION_DATE_FROM = "2021-01-01"
VALIDATION_DATE_TO = "2024-01-01"

OOS_DATE_FROM = "2024-01-01"
OOS_DATE_TO = "2027-01-01"


@dataclass(frozen=True)
class ResearchPeriod:
    """A pre-registered research period with a fixed role."""

    label: str
    role: str
    date_from: str
    date_to: str
    description: str


RESEARCH_PERIODS: dict[str, ResearchPeriod] = {
    "dev": ResearchPeriod(
        label="dev",
        role="development",
        date_from=DEVELOPMENT_DATE_FROM,
        date_to=DEVELOPMENT_DATE_TO,
        description=(
            "Development set (2015-2020): parameter exploration "
            "and hypothesis work happen here."
        ),
    ),
    "val": ResearchPeriod(
        label="val",
        role="validation",
        date_from=VALIDATION_DATE_FROM,
        date_to=VALIDATION_DATE_TO,
        description=(
            "Validation set (2021-2023): intermediate check after "
            "development, before any OOS consultation."
        ),
    ),
    "oos": ResearchPeriod(
        label="oos",
        role="out-of-sample-lockbox",
        date_from=OOS_DATE_FROM,
        date_to=OOS_DATE_TO,
        description=(
            "Out-of-sample lockbox (2024-2026): reserved, must not "
            "be consulted during development (roadmap §74)."
        ),
    ),
}

OOS_LOCKBOX_LABEL = "oos"

# Ordered from oldest to most recent; used for contiguity checks.
PERIOD_ORDER: tuple[str, ...] = ("dev", "val", "oos")


def resolve_period(
    label: str,
) -> ResearchPeriod:
    """Resolve a period label (dev/val/oos)."""
    key = label.strip().lower()

    try:
        return RESEARCH_PERIODS[key]
    except KeyError:
        raise ValueError(
            f"unknown period {label!r}; valid periods: "
            + ", ".join(PERIOD_ORDER)
        ) from None


def require_oos_allowed(
    *,
    allow_oos: bool,
) -> None:
    """
    Lockbox guard: consulting the OOS period requires an explicit
    opt-in. Without it the harness refuses to run OOS.
    """
    if not allow_oos:
        raise ValueError(
            "OOS period is a reserved lockbox (roadmap §74); "
            "pass --allow-oos to consult it explicitly"
        )
