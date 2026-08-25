"""Registry integrity — no database needed.

Every registry entry has a SQL file, every bind in the SQL is a field of the param/body
model (or a derived ``<list>_any`` flag), and every list field that is optional is guarded
by an ``_any`` flag in the SQL.
"""

import re
import typing

import pytest

from rgs_interface.registry import QUERIES, WRITES, sql_text
from rgs_interface.sql import _binds, prepare


def _is_list_field(model, name) -> bool:
    ann = model.model_fields[name].annotation
    origin = typing.get_origin(ann)
    if origin is list:
        return True
    if origin in (typing.Union, getattr(__import__("types"), "UnionType", None)):
        return any(typing.get_origin(a) is list for a in typing.get_args(ann))
    return False


@pytest.mark.parametrize("name", QUERIES)
def test_query_binds_match_params(name):
    q = QUERIES[name]
    sql = sql_text("queries", name)
    fields = set(q.params.model_fields)
    for bind in _binds(sql):
        if bind.endswith("_any"):
            base = bind[: -len("_any")]
            assert base in fields, f"{name}: {bind} has no list field {base}"
            assert _is_list_field(q.params, base), f"{name}: {base} is not a list field"
        else:
            assert bind in fields, f"{name}: bind :{bind} not in {q.params.__name__}"
    if "{rgs_mode}" in sql:
        assert "rgs_mode" in fields, f"{name}: templated SQL needs an rgs_mode param"


@pytest.mark.parametrize("name", QUERIES)
def test_optional_list_params_are_guarded(name):
    q = QUERIES[name]
    sql = sql_text("queries", name)
    for fname, f in q.params.model_fields.items():
        if _is_list_field(q.params, fname) and not f.is_required():
            assert f"{fname}_any" in _binds(sql), (
                f"{name}: optional list {fname} must be guarded by :{fname}_any in SQL"
            )


@pytest.mark.parametrize("name", WRITES)
def test_write_binds_match_body(name):
    w = WRITES[name]
    sql = sql_text("writes", name)
    assert _binds(sql) == set(w.body.model_fields), name


def test_prepare_derives_any_flags_and_drops_unreferenced():
    sql = "SELECT 1 WHERE (:ids_any = 0 OR x IN :ids) AND (:w IS NULL OR y = :w)"
    out_sql, p = prepare(sql, {"ids": None, "w": 3, "unused": 9})
    assert out_sql == sql
    assert p == {"ids": [], "ids_any": 0, "w": 3}
    _, p = prepare(sql, {"ids": [1, 2], "w": None})
    assert p == {"ids": [1, 2], "ids_any": 1, "w": None}


def test_prepare_substitutes_rgs_mode():
    out_sql, p = prepare("SELECT * FROM t_{rgs_mode} WHERE id IN :ids", {"rgs_mode": "app", "ids": [1]})
    assert out_sql == "SELECT * FROM t_app WHERE id IN :ids"
    assert p == {"ids": [1]}


def test_bind_regex_ignores_mysql_cast_syntax():
    assert _binds("SELECT a::int, :b FROM t") == {"b"}


def test_every_row_model_forbids_or_allows_extra_explicitly():
    for name, q in QUERIES.items():
        assert q.row.model_config.get("extra") in ("forbid", "allow"), name


def test_route_names_are_url_safe():
    assert all(re.fullmatch(r"[a-z_]+", n) for n in [*QUERIES, *WRITES])
