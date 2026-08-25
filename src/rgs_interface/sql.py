"""SqlBackend — runs registry queries directly against MySQL/MariaDB."""

from __future__ import annotations

import logging
import re

import pandas as pd
from pydantic import BaseModel
from sqlalchemy import bindparam, event, text
from sqlalchemy.engine import Engine

from rgs_interface.registry import QUERIES, WRITES, sql_text

logger = logging.getLogger(__name__)

_BIND_RE = re.compile(r"(?<!:):([A-Za-z_]\w*)")


def _binds(sql: str) -> set[str]:
    """Names of ``:param`` binds referenced in a SQL text."""
    return set(_BIND_RE.findall(sql))


def prepare(sql: str, params: dict) -> tuple[str, dict]:
    """Apply registry bind conventions: ``{rgs_mode}`` substitution, ``<list>_any``
    flags, ``None`` lists → ``[]``, and drop params the SQL doesn't reference."""
    p = dict(params)
    if "rgs_mode" in p:
        sql = sql.format(rgs_mode=p.pop("rgs_mode"))
    referenced = _binds(sql)
    for k, v in list(p.items()):
        flag = f"{k}_any"
        if flag in referenced:
            p[flag] = int(bool(v))
        if v is None and (flag in referenced or f"{k}_any" in referenced):
            p[k] = []
    return sql, {k: v for k, v in p.items() if k in referenced}


def _statement(sql: str, params: dict):
    stmt = text(sql)
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            stmt = stmt.bindparams(bindparam(k, expanding=True))
    return stmt


class SqlBackend:
    @classmethod
    def from_config(cls, read_only: bool = True, **engine_kwargs) -> "SqlBackend":
        """Engine from DB_* credentials (env, .env or ~/.rgs_config.yaml)."""
        from rgs_interface.config import make_engine

        return cls(make_engine(**engine_kwargs), read_only=read_only)

    def __init__(self, engine: Engine, read_only: bool = True):
        if engine is None:
            raise ValueError("SqlBackend needs a SQLAlchemy engine (got None)")
        self.engine = engine
        self.read_only = read_only
        if read_only:

            @event.listens_for(engine, "connect")
            def _set_read_only(dbapi_conn, _record):
                with dbapi_conn.cursor() as cur:
                    cur.execute("SET SESSION TRANSACTION READ ONLY")

    def fetch(self, name: str, **params) -> pd.DataFrame:
        q = QUERIES[name]
        p = q.params(**params).model_dump()
        sql, p = prepare(sql_text("queries", name), p)
        stmt = _statement(sql, p)
        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn, params=p, dtype_backend="numpy_nullable")

    def write(self, name: str, body: BaseModel) -> int:
        if self.read_only:
            raise PermissionError("SqlBackend was opened read_only; writes are disabled")
        w = WRITES[name]
        if not isinstance(body, w.body):
            body = w.body.model_validate(body)
        params = body.to_params_dict() if hasattr(body, "to_params_dict") else body.model_dump()
        stmt = text(sql_text("writes", name))
        with self.engine.begin() as conn:
            result = conn.execute(stmt, params)
            if result.rowcount != 1:
                raise RuntimeError(f"write {name}: expected 1 row inserted, got {result.rowcount}")
            return int(result.lastrowid)

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
