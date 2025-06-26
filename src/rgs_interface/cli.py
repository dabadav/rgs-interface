from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
from rgs_interface.data.interface import DatabaseInterface

app = typer.Typer(help="RGS Data CLI")

credentials_app = typer.Typer(help="Manage RGS credentials.")
app.add_typer(credentials_app, name="credentials")


def _save_rgs_data(patient_ids: List[int], rgs_mode: str, output_file: Optional[Path]):
    db_handler = DatabaseInterface()
    out_file = output_file or Path(f"rgs_{rgs_mode}.csv")
    db_handler.fetch_rgs_data(patient_ids, rgs_mode=rgs_mode, output_file=out_file)
    typer.echo(f"Data saved to {out_file}")


@credentials_app.command("set")
def set_credentials(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing credentials without prompting."
    )
):
    """
    Setup or overwrite credentials for RGS data access.
    """
    from rgs_interface.config import get_config, prompt_non_empty, save_to_yaml

    existing = get_config()
    if existing and not force:
        typer.echo("Credentials already exist.")
        if not typer.confirm("Do you want to overwrite them?"):
            typer.echo("Aborted.")
            raise typer.Exit()

    db_user = prompt_non_empty("Enter DB User: ")
    while True:
        db_pass = prompt_non_empty("Enter DB Password: ", is_password=True)
        db_pass_confirm = prompt_non_empty("Confirm DB Password: ", is_password=True)
        if db_pass == db_pass_confirm:
            break
        typer.echo("Passwords do not match. Please try again.")
    db_host = prompt_non_empty("Enter DB Host (e.g., localhost): ")
    db_name = prompt_non_empty("Enter DB Name: ")

    save_to_yaml(db_user, db_pass, db_host, db_name)
    typer.echo("Credentials saved successfully.")


@credentials_app.command("check")
def check_credentials():
    """
    Check if credentials are set and display their source.
    """
    from rgs_interface.config import CONFIG_FILE, ENV_FILE, get_config

    config = get_config()
    if config:
        typer.echo("Credentials are set.")
        if ENV_FILE.exists():
            typer.echo(f"Loaded from: {ENV_FILE}")
        elif CONFIG_FILE.exists():
            typer.echo(f"Loaded from: {CONFIG_FILE}")
    else:
        typer.echo("No credentials found.")


@app.command()
def fetch_rgs(
    patients: Optional[List[int]] = typer.Option(None, help="List of patient IDs."),
    patients_file: Optional[Path] = typer.Option(
        None, help="Path to a text file containing patient IDs (one per line)."
    ),
    hospital: Optional[List[int]] = typer.Option(None, help="List of hospital IDs."),
    study: Optional[str] = typer.Option(
        None, help="Study ID to fetch all patients for a study."
    ),
    rgs_mode: str = typer.Option("app", help="Mode for RGS data (default: 'app')."),
    output_file: Optional[Path] = typer.Option(
        None, help="Path to save the output file."
    ),
):
    """Load RGS data by patient IDs, hospital IDs, or study ID."""
    db_handler = DatabaseInterface()
    patient_ids = None
    if patients_file:
        with open(patients_file, "r") as f:
            patient_ids = [int(line.strip()) for line in f if line.strip().isdigit()]
    elif patients:
        patient_ids = patients
    elif hospital:
        patient_ids = db_handler.fetch_patients_by_hospital(hospital)
    elif study:
        patient_ids = db_handler.fetch_patients_by_study(study)
    else:
        typer.echo(
            "[ERROR] Provide one of --patients, --patients-file, --hospital, or --study."
        )
        raise typer.Exit(code=1)
    unique_patient_ids = normalize_patient_ids(patient_ids)
    if not unique_patient_ids:
        typer.echo("[ERROR] No patient IDs found after deduplication.")
        raise typer.Exit(code=1)
    _save_rgs_data(unique_patient_ids, rgs_mode, output_file)


def normalize_patient_ids(patient_ids) -> list[int]:
    """Convert patient_ids (DataFrame, Series, list, or None) to a unique sorted list of ints."""
    if patient_ids is None:
        return []
    if isinstance(patient_ids, pd.DataFrame):
        if len(patient_ids.columns) > 0:
            patient_ids = patient_ids["PATIENT_ID"].tolist()
        else:
            return []
    elif hasattr(patient_ids, "tolist"):
        patient_ids = patient_ids.tolist()
    elif not isinstance(patient_ids, list):
        return []
    # Remove None and deduplicate
    return sorted({int(pid) for pid in patient_ids if pid is not None})


@app.command()
def list_patients(
    hospital: Optional[List[int]] = typer.Option(None, help="List of hospital IDs."),
    study: Optional[str] = typer.Option(None, help="Study ID to list patients for."),
):
    """List patient IDs by hospital or study."""
    db_handler = DatabaseInterface()
    if hospital:
        patient_ids = db_handler.fetch_patients_by_hospital(hospital)
        unique_patient_ids = normalize_patient_ids(patient_ids)
        if not unique_patient_ids:
            typer.echo("[ERROR] No patient IDs found for the given hospital(s).")
            raise typer.Exit(code=1)
        typer.echo(f"Patients in hospital(s) {hospital}: {unique_patient_ids}")
    elif study:
        patient_ids = db_handler.fetch_patients_by_study(study)
        unique_patient_ids = normalize_patient_ids(patient_ids)
        if not unique_patient_ids:
            typer.echo("[ERROR] No patient IDs found for the given study.")
            raise typer.Exit(code=1)
        typer.echo(f"Patients in study {study}: {unique_patient_ids}")
    else:
        typer.echo("[ERROR] Provide --hospital or --study to list patients.")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
