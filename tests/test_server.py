"""Server behaviour with a stub backend — auth, scopes, envelope, parquet, validation."""

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from rgs_interface import server
from rgs_interface.registry import QUERIES

PROTOCOLS = pd.DataFrame(
    {
        "PROTOCOL_ID": [200, 201],
        "PROTOCOL_NAME": ["a", "b"],
        "PROTOCOL_TYPE_ID": [1, 2],
        "PROTOCOL_TYPE_NAME": ["motor", "cognitive"],
    }
)


class StubBackend:
    def __init__(self, frame=PROTOCOLS):
        self.frame = frame
        self.calls = []

    def fetch(self, name, **params):
        self.calls.append((name, params))
        return self.frame

    def write(self, name, body):
        self.calls.append((name, body))
        return 42


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_TOKENS", "rtok:supervisor:r,wtok:aicdss:rw")
    monkeypatch.setattr(server, "_backend", StubBackend())
    return TestClient(server.app)


R = {"Authorization": "Bearer rtok"}
W = {"Authorization": "Bearer wtok"}


def test_missing_token_401(client):
    assert client.get("/v1/protocols").status_code == 401


def test_bad_token_401(client):
    assert client.get("/v1/protocols", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_json_envelope(client):
    r = client.get("/v1/protocols", headers=R)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["rows"][0]["PROTOCOL_ID"] == 200


def test_parquet_roundtrip(client):
    r = client.get("/v1/protocols", headers={**R, "Accept": server.PARQUET})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(server.PARQUET)
    df = pd.read_parquet(io.BytesIO(r.content))
    pd.testing.assert_frame_equal(df, PROTOCOLS)


def test_params_are_validated_and_forwarded(client, monkeypatch):
    monkeypatch.setenv("API_VALIDATE", "0")  # stub returns a protocols frame for any query
    stub = server._backend
    r = client.get("/v1/staging", params={"patient_ids": [1, 2], "week": 4}, headers=R)
    assert r.status_code == 200
    name, params = stub.calls[-1]
    assert name == "staging" and params["patient_ids"] == [1, 2] and params["week"] == 4


def test_unknown_param_422(client):
    assert client.get("/v1/staging", params={"patient_ids": 1, "bogus": 1}, headers=R).status_code == 422


def test_missing_required_param_422(client):
    assert client.get("/v1/staging", headers=R).status_code == 422


def test_contract_violation_500(client, monkeypatch):
    bad = PROTOCOLS.rename(columns={"PROTOCOL_NAME": "NAME"})
    monkeypatch.setattr(server, "_backend", StubBackend(bad))
    r = client.get("/v1/protocols", headers=R)
    assert r.status_code == 500
    assert "ProtocolRow" in r.json()["detail"]


def test_write_requires_rw_scope(client):
    body = {
        "patient_id": 1, "protocol_id": 200, "starting_date": "2026-08-25",
        "ending_date": "2026-09-01", "weekday": "MONDAY", "session_duration": 300,
        "recommendation_id": "8b5f1a2e-1c3d-4e5f-8a9b-0c1d2e3f4a5b",
        "weeks_since_start": 3, "status": "PENDING",
    }
    assert client.post("/v1/staging", json=body, headers=R).status_code == 403
    r = client.post("/v1/staging", json=body, headers=W)
    assert r.status_code == 200 and r.json() == {"id": 42}


def test_write_body_validated(client):
    bad = {"patient_id": 1}
    assert client.post("/v1/staging", json=bad, headers=W).status_code == 422


def test_every_query_has_a_route(client):
    paths = {r.path for r in server.app.routes}
    for name in QUERIES:
        assert f"/v1/{name}" in paths


def test_openapi_has_typed_rows(client):
    spec = client.get("/openapi.json").json()
    assert "ProtocolRow" in spec["components"]["schemas"]
