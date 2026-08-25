"""RGS DB API — FastAPI app over the registry.

One ``GET /v1/<name>`` per read query, one ``POST /v1/<name>`` per write. Params/bodies are
validated by the registry models; every read response is validated against its row model
before serialisation (``API_VALIDATE=0`` disables — escape hatch, not a plan).

Env:
  API_TOKENS   "token:consumer:scope,..."  scope is "r" or "rw"
  API_VALIDATE "1" (default) | "0"
  DB_*         see rgs_interface.config

Run:  uvicorn rgs_interface.server:app --host 0.0.0.0 --port 8000
"""


import io
import logging
import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from pydantic import TypeAdapter, ValidationError

from rgs_interface.registry import QUERIES, WRITES
from rgs_interface.sql import SqlBackend

log = logging.getLogger("rgs_interface.server")

PARQUET = "application/vnd.apache.parquet"


def _validate() -> bool:
    return os.environ.get("API_VALIDATE", "1") == "1"

app = FastAPI(title="RGS DB API", version="1")

# ---------------------------------------------------------------- backend

_backend: SqlBackend | None = None


def backend() -> SqlBackend:
    """Lazily built so tests can inject a stub via ``server._backend``."""
    global _backend
    if _backend is None:
        _backend = SqlBackend.from_config(read_only=False)
    return _backend


# ---------------------------------------------------------------- auth


def _tokens() -> dict[str, tuple[str, str]]:
    raw = os.environ.get("API_TOKENS", "")
    out: dict[str, tuple[str, str]] = {}
    for item in filter(None, (s.strip() for s in raw.split(","))):
        try:
            token, consumer, scope = item.split(":")
        except ValueError as e:
            raise RuntimeError("API_TOKENS entries must be token:consumer:scope") from e
        if scope not in ("r", "rw"):
            raise RuntimeError(f"API_TOKENS scope must be r or rw, got {scope!r}")
        out[token] = (consumer, scope)
    return out


def auth(authorization: Annotated[str | None, Header()] = None) -> tuple[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    entry = _tokens().get(authorization.removeprefix("Bearer ").strip())
    if entry is None:
        raise HTTPException(401, "invalid token")
    return entry


def auth_write(entry: Annotated[tuple[str, str], Depends(auth)]) -> tuple[str, str]:
    if "w" not in entry[1]:
        raise HTTPException(403, f"consumer {entry[0]!r} has read-only scope")
    return entry


# ---------------------------------------------------------------- routes


def _make_get(name: str, q):
    Params = q.params  # noqa: N806 — evaluated now, so the closure captures this query's model

    async def handler(
        request: Request,
        params: Annotated[Params, Query()],
        who: Annotated[tuple[str, str], Depends(auth)],
    ):
        df = backend().fetch(name, **params.model_dump())
        rows_json = df.to_json(orient="records", date_format="iso")
        if _validate():
            try:
                TypeAdapter(list[q.row]).validate_json(rows_json)
            except ValidationError as e:
                log.error("contract violation on %s for %s: %s", name, who[0], e.errors()[:3])
                raise HTTPException(500, f"{name}: response does not match {q.row.__name__}")
        log.info("%s %s rows=%d", who[0], name, len(df))
        if PARQUET in request.headers.get("accept", ""):
            buf = io.BytesIO()
            df.to_parquet(buf, index=False)
            return Response(buf.getvalue(), media_type=PARQUET)
        return Response(
            f'{{"rows":{rows_json},"count":{len(df)}}}', media_type="application/json"
        )

    handler.__name__ = f"get_{name}"
    return handler


def _make_post(name: str, w):
    Body = w.body  # noqa: N806

    async def handler(
        body: Body,
        who: Annotated[tuple[str, str], Depends(auth_write)],
    ):
        new_id = backend().write(name, body)
        log.info("%s POST %s id=%s", who[0], name, new_id)
        return {"id": new_id}

    handler.__name__ = f"post_{name}"
    return handler


for _name, _q in QUERIES.items():
    app.add_api_route(
        f"/v1/{_name}",
        _make_get(_name, _q),
        methods=["GET"],
        name=_name,
        response_model=list[_q.row],
        summary=f"Read {_name}",
    )

for _name, _w in WRITES.items():
    app.add_api_route(
        f"/v1/{_name}",
        _make_post(_name, _w),
        methods=["POST"],
        name=f"post_{_name}",
        summary=f"Insert one row into {_name}",
    )


@app.get("/v1/health")
def health():
    try:
        backend().fetch("protocols")
        return {"status": "ok", "db": True}
    except Exception as e:  # pragma: no cover — only reached when DB is down
        log.error("health check failed: %s", e)
        raise HTTPException(503, "database unreachable")
