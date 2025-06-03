from dataclasses import dataclass, asdict
from datetime import date
from enum import Enum
from typing import Union

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
    DELTA_DM = "delta_dm"
    ADHERENCE = "adherence"
    PPF = "ppf"
    CONTRIB = "contrib"

@dataclass
class PrescriptionStagingRow:
    patient_id: int
    protocol_id: int
    starting_date: date
    ending_date: date
    weekday: WeekdayEnum
    session_duration: int
    recommendation_id: int
    weeks_since_start: int
    status: PrescriptionStatusEnum

    def __post_init__(self):
        if not isinstance(self.patient_id, int):
            _type = type(self.patient_id)
            raise TypeError(f"patient_id must be an integer. Your input - {self.patient_id}, {_type}")
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
        if not isinstance(self.recommendation_id, int):
            raise TypeError("recommendation_id must be an integer.")
        if not isinstance(self.weeks_since_start, int) or self.weeks_since_start < 0:
            raise ValueError("weeks_since_start must be a non-negative integer.")
        if not isinstance(self.status, PrescriptionStatusEnum):
            raise TypeError("status must be an instance of PrescriptionStatusEnum.")

    def to_params_dict(self) -> dict:
        data = asdict(self)
        data['weekday'] = self.weekday.value
        data['status'] = self.status.value
        return data

@dataclass
class RecsysMetricsRow:
    patient_id: int
    protocol_id: int
    recommendation_id: int
    metric_date: date 
    metric_key: RecsysMetricKeyEnum
    metric_value: Union[float, int, str]

    def __post_init__(self):
        if not isinstance(self.patient_id, int):
            raise TypeError("patient_id must be an integer.")
        if not isinstance(self.protocol_id, int):
            raise TypeError("protocol_id must be an integer.")
        if not isinstance(self.recommendation_id, int):
            raise TypeError("recommendation_id must be an integer.")
        if not isinstance(self.metric_date, date):
            raise TypeError("metric_date must be a valid date object.")
        if not isinstance(self.metric_key, RecsysMetricKeyEnum):
            raise TypeError("metric_key must be an instance of RecsysMetricKeyEnum.")
        if not isinstance(self.metric_value, (float, int, str)):
            raise TypeError("metric_value must be a float, int, or string.")

    def to_params_dict(self) -> dict:
        data = asdict(self)
        data['metric_key'] = self.metric_key.value
        return data