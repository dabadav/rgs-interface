"""rgs_interface — the RGS database contract, two backends, and the API server.

    from rgs_interface import SqlBackend, HttpBackend
    db = HttpBackend("https://api.example", token)     # or SqlBackend(engine)
    df = db.fetch("staging", patient_ids=[4378], week=4)
"""

from rgs_interface.registry import QUERIES, WRITES

__all__ = ["QUERIES", "WRITES", "SqlBackend", "HttpBackend"]
__version__ = "1.0.0"


def __getattr__(name):  # lazy: keep core import free of sqlalchemy / requests
    if name == "SqlBackend":
        from rgs_interface.sql import SqlBackend

        return SqlBackend
    if name == "HttpBackend":
        from rgs_interface.http import HttpBackend

        return HttpBackend
    raise AttributeError(name)
