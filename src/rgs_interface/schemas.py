"""Write bodies — the write contract.

Pydantic versions of the rows ai-cdss inserts. Field names and the ``from_row`` /
``to_params_dict`` helpers are kept so the ai-cdss call sites stay unchanged.
"""

from datetime import date, timedelta
from enum import Enum
from typing import Union
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator


class WeekdayEnum(Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class PrescriptionStatusEnum(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RecsysMetricKeyEnum(Enum):
    SCORE = "score"
    DELTA_DM = "delta_dm"
    ADHERENCE_RECENT = "recent_adherence"
    PPF = "ppf"
    CONTRIB = "contrib"
    USAGE = "total_usage"
    USAGE_WEEK = "usage_week"
    SESSION_INDEX = "total_prescribed_sessions"


class PrescriptionStagingRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    protocol_id: int
    starting_date: date
    ending_date: date
    weekday: WeekdayEnum
    session_duration: int = Field(gt=0)
    recommendation_id: UUID
    weeks_since_start: int = Field(ge=0)
    status: PrescriptionStatusEnum

    @model_validator(mode="after")
    def _dates_ordered(self):
        if self.ending_date < self.starting_date:
            raise ValueError("ending_date cannot be before starting_date.")
        return self

    def to_params_dict(self) -> dict:
        d = self.model_dump()
        d["weekday"] = self.weekday.value
        d["status"] = self.status.value
        d["recommendation_id"] = str(self.recommendation_id)
        return d

    @classmethod
    def from_row(
        cls,
        row: pd.Series,
        recommendation_id: UUID,
        start: date | None = None,
        duration: int = 300,
        status: PrescriptionStatusEnum = PrescriptionStatusEnum.PENDING,
    ) -> "PrescriptionStagingRow":
        start = start or date.today()
        return cls(
            patient_id=int(row["PATIENT_ID"]),
            protocol_id=int(row["PROTOCOL_ID"]),
            starting_date=start,
            ending_date=start + timedelta(days=7),
            weekday=(
                WeekdayEnum(row["WEEKDAY"])
                if isinstance(row["WEEKDAY"], str)
                else list(WeekdayEnum)[int(row["WEEKDAY"])]
            ),
            session_duration=duration,
            recommendation_id=recommendation_id,
            weeks_since_start=int(row["WEEKS_SINCE_START"]),
            status=status,
        )


class RecsysMetricsRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    protocol_id: int
    recommendation_id: UUID
    metric_date: date
    metric_key: RecsysMetricKeyEnum
    metric_value: Union[float, int, str, None]

    def to_params_dict(self) -> dict:
        d = self.model_dump()
        d["metric_key"] = self.metric_key.value
        d["recommendation_id"] = str(self.recommendation_id)
        return d

    @classmethod
    def from_row(
        cls, row: pd.Series, recommendation_id: UUID, metric_date: date | None = None
    ) -> "RecsysMetricsRow":
        return cls(
            patient_id=int(row["PATIENT_ID"]),
            protocol_id=int(row["PROTOCOL_ID"]),
            recommendation_id=recommendation_id,
            metric_date=metric_date or date.today(),
            metric_key=RecsysMetricKeyEnum[row["KEY"]],
            metric_value=None if pd.isna(row["VALUE"]) else row["VALUE"],
        )
