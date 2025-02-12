import pandas as pd
from sqlalchemy import text
import importlib.resources
from recsys_interface import sql
from recsys_interface.db import get_db_engine

def fetch_rgs_data(patient_ids, rgs_mode="plus", include_dms=False, output_file=f"rgs_interactions.csv"):
    """
    Fetch RGS interaction data for given patient IDs and save it as a CSV file.

    :param patient_ids: List of patient IDs to filter data.
    :param output_file: Name of the CSV file to save the output.
    """
    engine = get_db_engine()
    if not engine:
        return None  # Exit if connection fails

    try:
        # Load SQL query from file
        sql_path = importlib.resources.files(sql) / "query.sql"

        with sql_path.open("r") as file:
            sql_template = file.read()

        # Inject dynamic table name safely
        sql_query = sql_template.format(rgs_mode=rgs_mode)

        # Convert patient IDs to a parameterized query
        query_text = text(sql_query)
        params = {"patient_ids": tuple(patient_ids)}

        # Execute the query
        with engine.connect() as connection:
            df = pd.read_sql(query_text, connection, params=params)

        if include_dms:
            output_file_dms = output_file.replace(".csv", f"_dms.csv")
            output_file_dms_all = output_file.replace(".csv", f"_dms_all.csv")
            df_dms = fetch_dms_data(rgs_mode=rgs_mode, output_file=output_file_dms)
            df_all = df.merge(df_dms, on=["PATIENT_ID","SESSION_ID","PROTOCOL_ID"], how="left")
            df_all.to_csv(output_file_dms_all, index=False)

        else:
            df.to_csv(output_file, index=False)
            print(f"Data successfully saved to {output_file}")
            return df

    except Exception as e:
        print(f"Query execution failed: {e}")

        return None

    finally:
        engine.dispose()
        print("Database engine closed")

        return None

def fetch_dms_data(rgs_mode="plus", output_file="rgs_data_dms.csv"):
    """Fetch all difficulty modulator data in long format."""

    engine = get_db_engine()
    if not engine:
        return None

    sql_query = f"""
    SELECT
        SESSION_ID, PATIENT_ID, PROTOCOL_ID, GAME_MODE, SECONDS_FROM_START, PARAMETER_KEY, PARAMETER_VALUE
    FROM difficulty_modulators_{rgs_mode}
    """

    with engine.connect() as connection:
        df = pd.read_sql(text(sql_query), connection)

    print(f"Data of DMs retrieved.")

    df = pivot_difficulty_modulators(df)
    df.to_csv(output_file, index=False)
    print(f"Data of DMs, on wide format, successfully saved to {output_file}")

    return df

def fetch_patients_in_hospital(hospital_ids):
    engine = get_db_engine()
    if not engine:
        return None  # Exit if connection fails

    try:
        hospital_id_str = ','.join(map(str, hospital_ids))

        query = f"""
        SELECT PATIENT_ID
        FROM `patient`
        WHERE HOSPITAL_ID in ({hospital_id_str});
        """

        df = pd.read_sql(query, engine)
        patient_ids = df["PATIENT_ID"].tolist()
        return patient_ids

    except Exception as e:
        print(f"Query execution failed: {e}")

    finally:
        engine.dispose()
        print("Database engine closed")

def save_to_csv(df, output_file="rgs_interactions.csv"):
    """
    Save a DataFrame to CSV.

    :param df: Pandas DataFrame to save.
    :param output_file: File name to save as CSV.
    """
    if df is not None and not df.empty:
        df.to_csv(output_file, index=False)
        print(f"Data saved to {output_file}")
    else:
        print("No data available to save.")

def pivot_difficulty_modulators(df):
    """Pivot difficulty modulator data from long format to wide format."""

    # Pivot table to convert PARAMETER_KEY values into columns
    df_pivot = df.pivot_table(
        index=["SESSION_ID", "PATIENT_ID", "PROTOCOL_ID", "GAME_MODE", "SECONDS_FROM_START"],
        columns="PARAMETER_KEY",
        values="PARAMETER_VALUE",
        aggfunc="max"  # Or use first(), mean(), etc.
    ).reset_index()

    # Rename columns (flatten MultiIndex)
    df_pivot.columns.name = None  # Remove index name
    df_pivot = df_pivot.rename_axis(None, axis=1)  # Reset column names

    return df_pivot

# Test the function
if __name__ == '__main__':

    patient_ids = [
        1347, 1348, 1349, 1454, 1455, 1456, 1457, 1458, 1459, 1460, 1477,
        1478, 1479, 1480, 1481, 1482, 1484, 2332, 2333, 2334, 2335, 2336,
        2422, 2423, 2569, 2607, 2628, 2659, 2660, 2661, 2662, 2861, 2862,
        2864, 2865, 2866, 2882, 2886, 2897, 2930, 2947, 2967, 3026, 3084,
        3085, 3086, 3088, 3089, 3096, 3097, 3163, 3167, 3168, 3316, 3322
    ]

    data = fetch_rgs_data(patient_ids)
