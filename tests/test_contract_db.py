"""Parity against a real database — SqlBackend == HTTP path, rows validate.

Runs only when ``RGS_TEST_DB_URL`` is set (read-only user is enough), e.g.
``mysql+pymysql://user:pass@host/global_prod``. Uses the first cohort patients it finds
as sample ids, so it works against any environment with AISN data.
"""

import io
import os

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from sqlalchemy import create_engine

from rgs_interface import server
from rgs_interface.registry import QUERIES
from rgs_interface.sql import SqlBackend

DB_URL = os.environ.get("RGS_TEST_DB_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="RGS_TEST_DB_URL not set")


@pytest.fixture(scope="module")
def sql_backend():
    return SqlBackend(create_engine(DB_URL, pool_pre_ping=True), read_only=True)


@pytest.fixture(scope="module")
def client(sql_backend):
    os.environ["API_TOKENS"] = "t:test:r"
    server._backend = sql_backend
    return TestClient(server.app)


@pytest.fixture(scope="module")
def sample(sql_backend):
    cohort = sql_backend.fetch("cohort", exclude_control=True)
    pids = [int(x) for x in cohort["patient_id"].head(3)]
    assert pids, "no cohort patients in this database"
    return {
        "cohort": {},
        "protocols": {},
        "staging": {"patient_ids": pids},
        "staging_latest": {"patient_id": pids[0], "week": 1},
        "prescriptions": {"patient_ids": pids},
        "adherence": {"patient_id": pids[0]},
        "sessions": {"patient_id": pids[0], "status": "CLOSED"},
        "recsys_metrics": {"patient_id": pids[0]},
        "clinical_trials": {"patient_ids": pids},
        "patients": {"patient_ids": pids},
        "rgs_data": {"patient_ids": pids[:1]},
        "dm_data": {"patient_ids": pids[:1]},
        "pe_data": {"patient_ids": pids[:1]},
    }


@pytest.mark.parametrize("name", QUERIES)
def test_sql_http_parity(name, sql_backend, client, sample):
    params = sample[name]
    a = sql_backend.fetch(name, **params)
    r = client.get(
        f"/v1/{name}",
        params=QUERIES[name].params(**params).model_dump(mode="json", exclude_none=True),
        headers={"Authorization": "Bearer t", "Accept": server.PARQUET},
    )
    assert r.status_code == 200, r.text
    b = pd.read_parquet(io.BytesIO(r.content))
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
    if QUERIES[name].row.model_config.get("extra") == "forbid":
        assert tuple(a.columns) == QUERIES[name].columns
    TypeAdapter(list[QUERIES[name].row]).validate_json(
        a.to_json(orient="records", date_format="iso")
    )
