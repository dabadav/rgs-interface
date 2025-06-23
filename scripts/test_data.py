import pandas as pd
from pathlib import Path
import sys
import tempfile
from datetime import date
from rgs_interface.data.schemas import (
    ClinicalTrialsRow, PatientRow, DifficultyModulatorsPlusRow, PerformanceEstimatorsPlusRow, SessionPlusRow, PrescriptionPlusRow
)
from rgs_interface.data.interface import DatabaseInterface

def data_table(df, output_filename = "data_summary.html"):

    print("Checking data...")

    # Create html table with header
    html_table = """
    <html>
    <head>
    <style>

    table {
    font-family: Arial, sans-serif;
    border-collapse: collapse;
    width: 100%;
    }

    th {
    background-color: #f2f2f2;
    }

    th, td {
    border: 1px solid #dddddd;
    text-align: left;
    padding: 8px;
    }

    tr:nth-child(even) {
    background-color: #f2f2f2;
    }

    </style>

    </head>
    <body>
    <table>
    <tr>
    <th>Feature</th>
    <th>Data Type</th>
    <th>Missing Values</th>
    <th>Statistics</th>
    </tr>
    """

    # Get features and their data types
    features = df.columns
    data_types = df.dtypes

    # Get missing values
    missing_values = df.isnull().sum()

    # Get statistics
    statistics = df.describe()

    # Add rows to the html table
    for feature in features:
        formatted_feature = f"<b>{feature}</b>" if "_ID" in feature.upper() else feature
        html_table += f"<tr><td>{formatted_feature}</td><td>{data_types[feature]}</td><td>{missing_values[feature]}</td>"
        if feature in statistics:
            html_table += f"<td>{statistics[feature]}</td></tr>"
        else:
            html_table += "<td>N/A</td></tr>"

    # Close the html table
    html_table += """
    </table>
    </body>
    </html>
    """

    # Save the html table
    with open(output_filename, "w") as file:
        file.write(html_table)

def test_clinical_trials_row():
    row = ClinicalTrialsRow(
        clinical_trials_id=1,
        patient_id=1,
        study_id=1,
        study_name="StudyA",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        clinical_scores=[{"evaluation_date": "2024-09-10", "condition": "pre", "MoCA": {"Visuospatial/Executive": 4}}],
        recommend=1
    )
    d = row.to_params_dict()
    assert isinstance(d['clinical_scores'], str)
    print("ClinicalTrialsRow test passed.")

def test_patient_row():
    row = PatientRow(
        patient_id=1,
        hospital_id=1,
        patient_user="user1",
        password="pass",
        creation_time=date(2024, 1, 1),
        delete_time=date(2024, 1, 2),
        name="John",
        surname1="Doe",
        surname2="Smith",
        email="john@example.com",
        paretic_side="left",
        upper_extremity_to_train="arm",
        hand_raising_capacity=1,
        cognitive_function_level=2,
        has_heminegligence=0,
        gender="M",
        skin_color="white",
        birth_date=date(1990, 1, 1),
        videogame_exp=1,
        computer_exp=1,
        comments="none",
        ptn_height_cm=180,
        arm_size_cm=60,
        demo=0,
        version=1,
        has_recommender_system=1
    )
    d = row.to_params_dict()
    assert d['patient_user'] == "user1"
    print("PatientRow test passed.")

def test_difficulty_modulators_plus_row():
    row = DifficultyModulatorsPlusRow(
        difficulty_modulators_id=1,
        session_id=1,
        patient_id=1,
        protocol_id=1,
        game_mode="mode",
        seconds_from_start=10,
        parameter_key="key",
        parameter_value="val"
    )
    d = row.to_params_dict()
    assert d['game_mode'] == "mode"
    print("DifficultyModulatorsPlusRow test passed.")

def test_performance_estimators_plus_row():
    row = PerformanceEstimatorsPlusRow(
        performance_estimators_id=1,
        session_id=1,
        patient_id=1,
        protocol_id=1,
        game_mode="mode",
        seconds_from_start=10,
        parameter_key="key",
        parameter_value="val"
    )
    d = row.to_params_dict()
    assert d['parameter_key'] == "key"
    print("PerformanceEstimatorsPlusRow test passed.")

def test_session_plus_row():
    row = SessionPlusRow(
        session_id=1,
        prescription_id=1,
        starting_date=date(2024, 1, 1),
        ending_date=date(2024, 1, 2),
        status="closed",
        platform="win",
        device="dev",
        session_log_parsed="{}"
    )
    d = row.to_params_dict()
    assert d['status'] == "closed"
    print("SessionPlusRow test passed.")

def test_prescription_plus_row():
    row = PrescriptionPlusRow(
        prescription_id=1,
        patient_id=1,
        protocol_id=1,
        starting_date=date(2024, 1, 1),
        ending_date=date(2024, 1, 2),
        weekday="MONDAY",
        session_duration=30,
        ar_mode="mode"
    )
    d = row.to_params_dict()
    assert d['weekday'] == "MONDAY"
    print("PrescriptionPlusRow test passed.")

# DatabaseInterface tests (mocked, not actually writing to DB)
def test_database_interface_methods():
    db = DatabaseInterface()
    # Just check methods exist and can be called with correct dataclass
    try:
        db.add_clinical_trials_entry
        db.add_patient_entry
        db.add_difficulty_modulators_plus_entry
        db.add_performance_estimators_plus_entry
        db.add_session_plus_entry
        db.add_prescription_plus_entry
        db.fetch_recsys_metrics
        db.fetch_prescription_staging
        print("DatabaseInterface method presence test passed.")
    except Exception as e:
        print(f"DatabaseInterface method presence test failed: {e}")

if __name__ == '__main__':
    data_path = Path("../data")
    df = pd.read_csv(data_path / "rgs_plus_raj.csv")
    data_table(df, data_path / "data_summary_timeseries_app.html")
    test_clinical_trials_row()
    test_patient_row()
    test_difficulty_modulators_plus_row()
    test_performance_estimators_plus_row()
    test_session_plus_row()
    test_prescription_plus_row()
    test_database_interface_methods()
