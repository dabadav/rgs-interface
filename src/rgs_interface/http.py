"""HttpBackend — runs registry queries through the RGS DB API."""

from __future__ import annotations

import io

import pandas as pd
import requests
from pydantic import BaseModel
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from rgs_interface.registry import QUERIES, WRITES

PARQUET = "application/vnd.apache.parquet"


class HttpBackend:
    @classmethod
    def from_config(cls, **kwargs) -> "HttpBackend":
        """Client from RGS_API_URL / RGS_API_TOKEN (env, .env or ~/.rgs_config.yaml)."""
        from rgs_interface.config import get_api_config

        cfg = get_api_config()
        if not cfg:
            raise RuntimeError("API credentials not found (RGS_API_URL/RGS_API_TOKEN)")
        return cls(cfg["RGS_API_URL"], cfg["RGS_API_TOKEN"], **kwargs)

    def __init__(self, base_url: str, token: str, timeout: float = 120.0, retries: int = 3):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        retry = Retry(
            total=retries,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def fetch(self, name: str, **params) -> pd.DataFrame:
        q = QUERIES[name]
        p = q.params(**params).model_dump(mode="json", exclude_none=True)
        r = self.session.get(
            f"{self.base}/v1/{name}",
            params=p,
            headers={"Accept": PARQUET},
            timeout=self.timeout,
        )
        _raise(r)
        return pd.read_parquet(io.BytesIO(r.content))

    def write(self, name: str, body: BaseModel) -> int:
        w = WRITES[name]
        if not isinstance(body, w.body):
            body = w.body.model_validate(body)
        r = self.session.post(
            f"{self.base}/v1/{name}",
            json=body.model_dump(mode="json"),
            timeout=self.timeout,
        )
        _raise(r)
        return int(r.json()["id"])

    def close(self) -> None:
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _raise(r: requests.Response) -> None:
    if r.ok:
        return
    try:
        detail = r.json().get("detail", r.text)
    except ValueError:
        detail = r.text
    raise requests.HTTPError(f"{r.status_code} {r.request.method} {r.url}: {detail}", response=r)
