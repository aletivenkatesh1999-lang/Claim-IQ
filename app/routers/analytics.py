from datetime import (
    datetime,
    timezone,
)

import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import officer_or_admin


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


def claims_dataframe(
    db: Session
) -> pd.DataFrame:
    claims = (
        db.query(models.Claim)
        .all()
    )

    rows = []

    for claim in claims:
        rows.append(
            {
                "id": claim.id,
                "claim_number": (
                    claim.claim_number
                ),
                "policy_id": claim.policy_id,
                "status": claim.status.value,
                "created_at": claim.created_at,
                "updated_at": claim.updated_at
            }
        )

    return pd.DataFrame(rows)


@router.get(
    "/claims/summary"
)
def claims_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        officer_or_admin
    )
):
    df = claims_dataframe(
        db
    )

    if df.empty:
        return {
            "total_claims": 0,
            "status_breakdown": {},
            "approval_rate_percent": 0.0,
            "average_turnaround_hours": 0.0
        }

    total_claims = int(
        len(df)
    )

    status_counts = (
        df["status"]
        .value_counts()
        .to_dict()
    )

    approved_count = int(
        (
            df["status"]
            == models.ClaimStatus.approved.value
        ).sum()
    )

    rejected_count = int(
        (
            df["status"]
            == models.ClaimStatus.rejected.value
        ).sum()
    )

    decided_count = (
        approved_count
        + rejected_count
    )

    approval_rate = 0.0

    if decided_count > 0:
        approval_rate = round(
            (
                approved_count
                / decided_count
            )
            * 100,
            2
        )

    created = pd.to_datetime(
        df["created_at"],
        utc=True
    )

    updated = pd.to_datetime(
        df["updated_at"],
        utc=True
    )

    turnaround_hours = (
        updated - created
    ).dt.total_seconds() / 3600

    average_turnaround = round(
        float(
            turnaround_hours.mean()
        ),
        2
    )

    return {
        "total_claims": total_claims,
        "status_breakdown": {
            str(key): int(value)
            for key, value
            in status_counts.items()
        },
        "approval_rate_percent": approval_rate,
        "average_turnaround_hours": (
            average_turnaround
        )
    }


@router.get(
    "/claims/sla"
)
def claims_sla(
    sla_hours: int = 48,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        officer_or_admin
    )
):
    now = datetime.now(
        timezone.utc
    )

    active_statuses = {
        models.ClaimStatus.submitted,
        models.ClaimStatus.under_review
    }

    claims = (
        db.query(models.Claim)
        .all()
    )

    breaches = []

    for claim in claims:
        if claim.status not in active_statuses:
            continue

        created_at = claim.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        age_hours = (
            now - created_at
        ).total_seconds() / 3600

        if age_hours > sla_hours:
            breaches.append(
                {
                    "claim_id": claim.id,
                    "claim_number": (
                        claim.claim_number
                    ),
                    "status": (
                        claim.status.value
                    ),
                    "age_hours": round(
                        age_hours,
                        2
                    )
                }
            )

    return {
        "sla_hours": sla_hours,
        "breach_count": len(
            breaches
        ),
        "claims": breaches
    }