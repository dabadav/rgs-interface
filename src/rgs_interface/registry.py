"""Query registry — the single place a query is declared.

A read is ``name -> Query(params, row)`` with its SQL in ``queries/<name>.sql``; a write is
``name -> Write(body)`` with its SQL in ``writes/<name>.sql``. Both backends and the server
read this dict, so adding a query is: one .sql file, one param model, one line here.

Bind-parameter conventions used by the SQL files:

* ``:name`` — a scalar or list field of the param model. Lists expand to ``IN (...)``.
* ``:name_any`` — derived automatically for list fields: ``1`` when the list is non-empty,
  ``0`` when it is ``None``/empty. Lets optional list filters read
  ``(:ids_any = 0 OR col IN :ids)``.
* ``{rgs_mode}`` — substituted into the SQL text (table suffix), never bound.
"""

from dataclasses import dataclass
from datetime import date, datetime
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from rgs_interface import models as M
from rgs_interface import schemas as S

PatientIds = list[int]


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoParams(Params):
    pass


class CohortParams(Params):
    patient_id: int | None = None
    arm: str | None = None
    exclude_control: bool = False
    active: bool = False


class StagingParams(Params):
    patient_ids: PatientIds = Field(min_length=1, max_length=500)
    week: int | None = None
    status: str | None = None
    recommendation_id: str | None = None
    week_start: date | None = None


class StagingLatestParams(Params):
    patient_id: int
    week: int | None = None


class PrescriptionParams(Params):
    patient_ids: PatientIds = Field(min_length=1, max_length=500)
    active_from: datetime | None = None
    active_to: datetime | None = None


class PatientParams(Params):
    patient_id: int


class SessionParams(Params):
    patient_id: int
    status: str | None = None
    since: datetime | None = None
    until: datetime | None = None


class RecsysMetricParams(Params):
    patient_id: int
    recommendation_ids: list[str] | None = None


class ClinicalTrialParams(Params):
    patient_ids: PatientIds | None = Field(default=None, max_length=500)
    study_id: int | None = None
    due_today: bool = False
    with_scores: bool = False


class PatientsParams(Params):
    patient_ids: PatientIds | None = Field(default=None, max_length=500)
    hospital_ids: list[int] | None = None
    name_like: str | None = None


class RgsDataParams(Params):
    patient_ids: PatientIds = Field(min_length=1, max_length=500)
    rgs_mode: Literal["plus", "app"] = "plus"


@dataclass(frozen=True)
class Query:
    params: type[Params]
    row: type[BaseModel]

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(self.row.model_fields)


@dataclass(frozen=True)
class Write:
    body: type[BaseModel]


QUERIES: dict[str, Query] = {
    "cohort":          Query(CohortParams,        M.CohortRow),
    "protocols":       Query(NoParams,            M.ProtocolRow),
    "staging":         Query(StagingParams,       M.StagingRow),
    "staging_latest":  Query(StagingLatestParams, M.StagingLatest),
    "prescriptions":   Query(PrescriptionParams,  M.PrescriptionRow),
    "adherence":       Query(PatientParams,       M.AdherenceRow),
    "sessions":        Query(SessionParams,       M.SessionRow),
    "recsys_metrics":  Query(RecsysMetricParams,  M.RecsysMetricRow),
    "clinical_trials": Query(ClinicalTrialParams, M.ClinicalTrialRow),
    "patients":        Query(PatientsParams,      M.PatientRow),
    "rgs_data":        Query(RgsDataParams,       M.RgsDataRow),
    "dm_data":         Query(RgsDataParams,       M.DmRow),
    "pe_data":         Query(RgsDataParams,       M.PeRow),
}

WRITES: dict[str, Write] = {
    "staging":        Write(S.PrescriptionStagingRow),
    "recsys_metrics": Write(S.RecsysMetricsRow),
}


def sql_text(kind: Literal["queries", "writes"], name: str) -> str:
    return (files(f"rgs_interface.{kind}") / f"{name}.sql").read_text(encoding="utf-8")
