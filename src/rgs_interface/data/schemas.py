import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from enum import Enum
from typing import List, Union
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
    DELTA_DM = "delta_dm"
    ADHERENCE_RECENT = "adherence"
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
            weeks_since_start=0,  # Adjust as needed
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


@dataclass
class ClinicalTrialsRow:
    clinical_trials_id: int
    patient_id: int
    study_id: int
    study_name: str
    start_date: date
    end_date: date
    clinical_scores: List[dict]
    recommend: int  # 0 or 1

    def __post_init__(self):
        if not isinstance(self.patient_id, int):
            raise TypeError("patient_id must be an integer.")
        if not isinstance(self.study_id, int):
            raise TypeError("study_id must be an integer.")
        if not isinstance(self.study_name, str):
            raise TypeError("study_name must be a string.")
        if not isinstance(self.start_date, date):
            raise TypeError("start_date must be a valid date object.")
        if not isinstance(self.end_date, date):
            raise TypeError("end_date must be a valid date object.")
        if not isinstance(self.clinical_scores, list):
            raise TypeError("clinical_scores must be a list of dicts.")
        if not isinstance(self.recommend, int) or self.recommend not in (0, 1):
            raise ValueError("recommend must be 0 or 1.")

    def to_params_dict(self) -> dict:
        data = asdict(self)
        data["clinical_scores"] = json.dumps(self.clinical_scores)
        return data


@dataclass
class PatientRow:
    patient_id: int
    hospital_id: int
    patient_user: str
    password: str
    creation_time: date
    delete_time: date
    name: str
    surname1: str
    surname2: str
    email: str
    paretic_side: str
    upper_extremity_to_train: str
    hand_raising_capacity: int
    cognitive_function_level: int
    has_heminegligence: int
    gender: str
    skin_color: str
    birth_date: date
    videogame_exp: int
    computer_exp: int
    comments: str
    ptn_height_cm: int
    arm_size_cm: int
    demo: int
    version: int
    has_recommender_system: int

    def __post_init__(self):
        # Add type checks as needed
        pass

    def to_params_dict(self) -> dict:
        return asdict(self)


@dataclass
class DifficultyModulatorsPlusRow:
    difficulty_modulators_id: int
    session_id: int
    patient_id: int
    protocol_id: int
    game_mode: str
    seconds_from_start: int
    parameter_key: str
    parameter_value: str

    def __post_init__(self):
        pass

    def to_params_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerformanceEstimatorsPlusRow:
    performance_estimators_id: int
    session_id: int
    patient_id: int
    protocol_id: int
    game_mode: str
    seconds_from_start: int
    parameter_key: str
    parameter_value: str

    def __post_init__(self):
        pass

    def to_params_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionPlusRow:
    session_id: int
    prescription_id: int
    starting_date: date
    ending_date: date
    status: str
    platform: str
    device: str
    session_log_parsed: str

    def __post_init__(self):
        pass

    def to_params_dict(self) -> dict:
        return asdict(self)


@dataclass
class PrescriptionPlusRow:
    prescription_id: int
    patient_id: int
    protocol_id: int
    starting_date: date
    ending_date: date
    weekday: str
    session_duration: int
    ar_mode: str

    def __post_init__(self):
        pass

    def to_params_dict(self) -> dict:
        return asdict(self)
