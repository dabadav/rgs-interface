"""Row models — the read contract.

One pydantic model per registry query. Field names are the SQL column names verbatim;
field types are what the database must deliver. The server validates every response
against these before returning it, so a schema change on the DB host fails here, loudly,
instead of reaching a dashboard as wrong data.

Models marked ``extra="allow"`` wrap ``SELECT *`` queries whose full column list is fixed
once ``DESCRIBE`` has been run on the new host; lock them to ``forbid`` then.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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
