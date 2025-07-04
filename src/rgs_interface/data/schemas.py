from dataclasses import asdict, dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Union
from uuid import UUID

import pandas as pd


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


@dataclass
class PrescriptionStagingRow:
    patient_id: int
    protocol_id: int
    starting_date: date
    ending_date: date
    weekday: WeekdayEnum
    session_duration: int
    recommendation_id: UUID
    weeks_since_start: int
    status: PrescriptionStatusEnum

    def __post_init__(self):
        if not isinstance(self.patient_id, int):
            _type = type(self.patient_id)
            raise TypeError(
                f"patient_id must be an integer. Your input - {self.patient_id}, {_type}"
            )
        if not isinstance(self.protocol_id, int):
            raise TypeError("protocol_id must be an integer.")
        if not isinstance(self.starting_date, date):
            raise TypeError("starting_date must be a valid date object.")
        if not isinstance(self.ending_date, date):
            raise TypeError("ending_date must be a valid date object.")
        if self.ending_date < self.starting_date:
            raise ValueError("ending_date cannot be before starting_date.")
        if not isinstance(self.weekday, WeekdayEnum):
            raise TypeError("weekday must be an instance of WeekdayEnum.")
        if not isinstance(self.session_duration, int) or self.session_duration <= 0:
            raise ValueError("session_duration must be a positive integer.")
        if not isinstance(self.recommendation_id, UUID):
            raise TypeError("recommendation_id must be an uuid.")
        if not isinstance(self.weeks_since_start, int) or self.weeks_since_start < 0:
            raise ValueError("weeks_since_start must be a non-negative integer.")
        if not isinstance(self.status, PrescriptionStatusEnum):
            raise TypeError("status must be an instance of PrescriptionStatusEnum.")

    def to_params_dict(self) -> dict:
        data = asdict(self)
        data["weekday"] = self.weekday.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_row(
        cls,
        row: pd.Series,
        recommendation_id: UUID,
        start: date = date.today(),
        duration: int = 300,
        status: PrescriptionStatusEnum = PrescriptionStatusEnum.PENDING,
    ) -> "PrescriptionStagingRow":
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
            weeks_since_start=row["WEEKS_SINCE_START"],
            status=status,
        )


@dataclass
class RecsysMetricsRow:
    patient_id: int
    protocol_id: int
    recommendation_id: UUID
    metric_date: date
    metric_key: RecsysMetricKeyEnum
    metric_value: Union[float, int, str]

    def __post_init__(self):
        if not isinstance(self.patient_id, int):
            raise TypeError("patient_id must be an integer.")
        if not isinstance(self.protocol_id, int):
            raise TypeError("protocol_id must be an integer.")
        if not isinstance(self.recommendation_id, UUID):
            raise TypeError("recommendation_id must be an uuid.")
        if not isinstance(self.metric_date, date):
            raise TypeError("metric_date must be a valid date object.")
        if not isinstance(self.metric_key, RecsysMetricKeyEnum):
            raise TypeError("metric_key must be an instance of RecsysMetricKeyEnum.")
        if not isinstance(self.metric_value, (float, int, str, type(None))):
            raise TypeError("metric_value must be a float, int, str, or None.")

    def to_params_dict(self) -> dict:
        data = asdict(self)
        data["metric_key"] = self.metric_key.value
        return data

    @classmethod
    def from_row(
        cls, row: pd.Series, recommendation_id: UUID, metric_date: date = date.today()
    ) -> "RecsysMetricsRow":
        return cls(
            patient_id=int(row["PATIENT_ID"]),
            protocol_id=int(row["PROTOCOL_ID"]),
            recommendation_id=recommendation_id,
            metric_date=metric_date,
            metric_key=RecsysMetricKeyEnum[row["KEY"]],
            metric_value=None if pd.isna(row["VALUE"]) else row["VALUE"],
        )
