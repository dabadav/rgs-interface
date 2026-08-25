"""The contract: rows (reads) and bodies (writes).

Rows — one per registry query, what ``GET /v1/<name>`` returns. Field names are the SQL
column names verbatim; field types are what the database must deliver. The server
validates every response against these, so a schema change on the DB host fails here,
loudly, instead of reaching a dashboard as wrong data. Rows marked ``extra="allow"`` wrap
``SELECT *`` queries whose column list is fixed once ``DESCRIBE`` has been run on the new
host; lock them to ``forbid`` then.

Bodies — one per write, what ``POST /v1/<name>`` takes. Field names and the ``from_row`` /
``to_params_dict`` helpers follow the ai-cdss call sites so its upgrade stays small.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Union
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

# --------------------------------------------------------------------------- rows


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CohortRow(Row):
    patient_id: int
    patient_name: str
    hospital_name: str
    trial_arm: str
    trial_start: date
    trial_end: date
    trial_active: bool
    last_session_at: datetime | None
    days_without_session: int | None


class ProtocolRow(Row):
    PROTOCOL_ID: int
    PROTOCOL_NAME: str
    PROTOCOL_TYPE_ID: int
    PROTOCOL_TYPE_NAME: str


class StagingRow(Row):
    PRESCRIPTION_STAGING_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime
    WEEKDAY: str
    SESSION_DURATION: int
    RECOMMENDATION_ID: str | None
    WEEKS_SINCE_START: int
    STATUS: str


class StagingLatest(Row):
    max_week: int | None
    latest_recommendation_id: str | None


class PrescriptionRow(Row):
    PRESCRIPTION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime
    WEEKDAY: str
    SESSION_DURATION: int


class AdherenceRow(Row):
    PRESCRIPTION_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    WEEKDAY: str
    PRESCRIBED_DURATION: int
    SESSION_ID: int | None
    SESSION_DATE: datetime | None
    SESSION_STATUS: str | None
    RECORDED_DURATION: float | None


class SessionRow(Row):
    SESSION_ID: int
    PRESCRIPTION_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime | None
    STATUS: str


class RecsysMetricRow(Row):
    RECOMMENDATION_ID: str
    PROTOCOL_ID: int
    METRIC_KEY: str
    METRIC_VALUE: Decimal | None
    METRIC_DATE: datetime


class ClinicalTrialRow(Row):
    model_config = ConfigDict(extra="allow")  # SELECT * — lock after DESCRIBE on new host
    PATIENT_ID: int
    STUDY_ID: int
    START_DATE: date
    END_DATE: date
    RECOMMEND: int
    CLINICAL_SCORES: str | None


class PatientRow(Row):
    model_config = ConfigDict(extra="allow")  # SELECT * — lock after DESCRIBE on new host
    PATIENT_ID: int
    PATIENT_USER: str
    HOSPITAL_ID: int


class RgsDataRow(Row):
    PATIENT_ID: int
    PRESCRIPTION_ID: int
    SESSION_ID: int | None
    PROTOCOL_ID: int
    PRESCRIPTION_STARTING_DATE: datetime
    PRESCRIPTION_ENDING_DATE: datetime
    SESSION_DATE: datetime | None
    STATUS: str | None
    WEEKDAY_INDEX: int | None
    REAL_SESSION_DURATION: int | None
    PRESCRIBED_SESSION_DURATION: int
    SESSION_DURATION: int | None
    ADHERENCE: float | None
    DM_VALUE: float | None


class DmRow(Row):
    SESSION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    GAME_MODE: str
    SECONDS_FROM_START: int
    DM_KEY: str
    DM_VALUE: float | None


class PeRow(Row):
    SESSION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    GAME_MODE: str
    SECONDS_FROM_START: int
    PE_KEY: str
    PE_VALUE: float | None


# ------------------------------------------------------------------------- bodies


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
