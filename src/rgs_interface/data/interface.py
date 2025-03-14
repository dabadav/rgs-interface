import pandas as pd
from sqlalchemy import text
import importlib.resources
from rgs_interface import sql
from rgs_interface.db import get_db_engine

###########################
### ---- Get Data ---- ####
###########################

def fetch_rgs_data(patient_ids, rgs_mode="plus", output_file=None):
    """
    Fetch RGS interaction data for given patient IDs and save it as a CSV file.
    
    :param patients_ids: List of patient IDs to filter data.
    :param rgs_mode: RGS mode to filter data.
    :param output_file: Name of the CSV file to save the

    :return: DataFrame containing the RGS interaction data.
    """
    query_file="query.sql"
    return _fetch(
        query=query_file,
        params={"patient_ids": tuple(patient_ids)},
        rgs_mode=rgs_mode,
        output_file=output_file
    )

def fetch_timeseries_data(patient_ids, rgs_mode="plus", output_file=None):
    """
    Fetch timeseries RGS interaction data for given patient IDs.
    """
    # Hack as there is no multiindex in across tables
    dm = fetch_dm_data(patient_ids, rgs_mode)
    pe = fetch_pe_data(patient_ids, rgs_mode)
    return dm.merge(
        pe,
        on=["SESSION_ID", "PATIENT_ID", "PROTOCOL_ID", "GAME_MODE", "SECONDS_FROM_START"],
    )

def fetch_dm_data(patient_ids, rgs_mode="plus", output_file=None):
    """
    Fetch timeseries RGS interaction data for given patient IDs.
    """
    query_file="query_dm.sql"
    return _fetch(
        query=query_file,
        params={"patient_ids": tuple(patient_ids)},
        rgs_mode=rgs_mode,
        output_file=output_file
    )

def fetch_pe_data(patient_ids, rgs_mode="plus", output_file=None):
    """
    Fetch timeseries RGS interaction data for given patient IDs.
    """
    query_file="query_pe.sql"
    return _fetch(
        query=query_file,
        params={"patient_ids": tuple(patient_ids)},
        rgs_mode=rgs_mode,
        output_file=output_file
    )

### ---- Get IDs ---- ####

def fetch_patients_by_hospital(hospital_ids):
    """
    Fetch list of patient IDs from a given list of hospital IDs.
    """
    hospital_id_str = ','.join(map(str, hospital_ids))
    return _fetch(
        query=f"""
        SELECT PATIENT_ID
        FROM patient
        WHERE HOSPITAL_ID IN ({hospital_id_str});
        """
    )

def fetch_patients_by_name(pattern):
    """
    Fetch patient IDs based on a pattern match in the PATIENT_USER field.
    """
    return _fetch(
        query="SELECT * FROM patient WHERE PATIENT_USER LIKE :pattern;",
        params={"pattern": f"%{pattern}%"}
    )

def fetch_patients():
    return _fetch(
        query="SELECT * FROM patient"
    )

### ---- Handler ---- ####

def _fetch(query, params=None, rgs_mode=None, output_file=None, dtype_backend="numpy_nullable"):
    """
    Generalized function to fetch data from the database using either a SQL file name or a raw query string.

    :param query: SQL file name (string ending with '.sql') OR raw SQL query as a string.
    :param params: Dictionary of parameters to safely format the query.
    :param output_file: CSV file to save the results.
    :param dtype_backend: Backend for pandas DataFrame dtype (default: numpy_nullable).
    
    :return: DataFrame with query results.
    """
    engine = get_db_engine()
    if not engine:
        return None  # Exit if connection fails

    try:
        # Accepts SQL file or str
        if query.endswith(".sql"):
            sql_path = importlib.resources.files(sql) / query
            with sql_path.open("r") as file:
                sql_query = file.read()
        else:
            sql_query = query

        # Use parameterized query
        if rgs_mode:
            sql_query = sql_query.format(rgs_mode=rgs_mode)
        
        query_text = text(sql_query)

        # Execute query
        with engine.connect() as connection:
            df = pd.read_sql(query_text, connection, params=params, dtype_backend=dtype_backend)

        if output_file:
            df.to_csv(output_file, index=False)
            print(f"Data successfully saved to {output_file}")

        return df

    except Exception as e:
        print(f"Query execution failed: {e}")
        return None

    finally:
        engine.dispose()
        print("Database engine closed")
