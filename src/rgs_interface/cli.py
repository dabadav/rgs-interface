"""rgs-cli — credentials, ad-hoc fetches, patient lookups.

Talks to the RGS DB API by default (``RGS_API_URL`` / ``RGS_API_TOKEN`` from env or
``~/.rgs_config.yaml``). ``--direct`` uses a direct MySQL connection instead (only works
where port 3306 is reachable).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from rgs_interface.registry import QUERIES

app = typer.Typer(help="RGS Data CLI", no_args_is_help=True)
credentials_app = typer.Typer(help="Manage RGS credentials.")
app.add_typer(credentials_app, name="credentials")


def _backend(direct: bool):
    try:
        if direct:
            from rgs_interface.sql import SqlBackend

            return SqlBackend.from_config(read_only=True)
        from rgs_interface.http import HttpBackend

        return HttpBackend.from_config()
    except RuntimeError as e:
        typer.echo(f"{e}. Run: rgs-cli credentials set", err=True)
        raise typer.Exit(1)


def _parse_params(items: list[str]) -> dict:
    """``key=value`` pairs; comma-separated values become lists."""
    out: dict = {}
    for item in items:
        if "=" not in item:
            raise typer.BadParameter(f"expected key=value, got {item!r}")
        k, v = item.split("=", 1)
        out[k] = v.split(",") if "," in v else v
    return out


@credentials_app.command("set")
def set_credentials(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite without prompting."),
):
    """Store API url/token (and optionally direct DB credentials) in ~/.rgs_config.yaml."""
    from rgs_interface.config import get_api_config, prompt_non_empty, save_yaml

    if get_api_config() and not force and not typer.confirm("Credentials exist. Overwrite?"):
        raise typer.Exit()
    url = prompt_non_empty("API URL (e.g. https://api.rgs.example): ")
    token = prompt_non_empty("API token: ", is_password=True)
    values = {"RGS_API_URL": url, "RGS_API_TOKEN": token}
    if typer.confirm("Also store direct DB credentials (for --direct)?", default=False):
        values.update(
            DB_USER=prompt_non_empty("DB User: "),
            DB_PASS=prompt_non_empty("DB Password: ", is_password=True),
            DB_HOST=prompt_non_empty("DB Host: "),
            DB_NAME=prompt_non_empty("DB Name: "),
        )
    save_yaml(**values)
    typer.echo("Credentials saved.")


@credentials_app.command("check")
def check_credentials():
    """Show which credentials are configured and where they come from."""
    from rgs_interface.config import CONFIG_FILE, ENV_FILE, get_api_config, get_config

    api, db = get_api_config(), get_config()
    typer.echo(f"API : {'set (' + api['RGS_API_URL'] + ')' if api else 'not set'}")
    typer.echo(f"DB  : {'set (' + db['DB_HOST'] + ')' if db else 'not set'}")
    typer.echo(f"Sources: {ENV_FILE} {'✓' if ENV_FILE.exists() else '✗'}, {CONFIG_FILE} {'✓' if CONFIG_FILE.exists() else '✗'}")


@app.command()
def fetch(
    name: str = typer.Argument(..., help=f"Query name: {', '.join(QUERIES)}"),
    param: list[str] = typer.Option([], "--param", "-p", help="key=value; comma-separates lists"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="CSV/parquet path (by extension)"),
    direct: bool = typer.Option(False, "--direct", help="Use direct MySQL instead of the API"),
):
    """Run a registry query and print or save the result."""
    if name not in QUERIES:
        raise typer.BadParameter(f"unknown query {name!r}; choose from {', '.join(QUERIES)}")
    df = _backend(direct).fetch(name, **_parse_params(param))
    if output is None:
        typer.echo(df.to_string(max_rows=50))
        typer.echo(f"[{len(df)} rows]")
    elif output.suffix == ".parquet":
        df.to_parquet(output, index=False)
        typer.echo(f"Saved {len(df)} rows to {output}")
    else:
        df.to_csv(output, index=False)
        typer.echo(f"Saved {len(df)} rows to {output}")


@app.command("list-patients")
def list_patients(
    hospital: list[int] = typer.Option([], "--hospital", help="Hospital IDs"),
    name: Optional[str] = typer.Option(None, "--name", help="PATIENT_USER LIKE pattern, e.g. 'AI%'"),
    direct: bool = typer.Option(False, "--direct"),
):
    """List patient IDs by hospital and/or name pattern."""
    if not hospital and not name:
        raise typer.BadParameter("provide --hospital and/or --name")
    df = _backend(direct).fetch(
        "patients", hospital_ids=hospital or None, name_like=name
    )
    ids = sorted(int(x) for x in df["PATIENT_ID"].dropna().unique())
    typer.echo(f"{len(ids)} patients: {ids}")


if __name__ == "__main__":
    app()
