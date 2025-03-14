import pandas as pd
from sqlalchemy import text
import importlib.resources
from recsys_interface import sql
from recsys_interface.db import get_db_engine
# import time
# import functools
# def timeit(func):
#     """Decorator to measure execution time of a function."""
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         start_time = time.perf_counter()
#         result = func(*args, **kwargs)
#         end_time = time.perf_counter()
#         elapsed_time = end_time - start_time
#         print(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds")
#         return result
#     return wrapper

###########################
### ---- Get Data ---- ####
###########################

def _fetch_data(patient_ids, rgs_mode="plus", query_file="query.sql", output_file=None):
    """
    Base method to fetch RGS interaction data for given patient IDs and save it as a CSV file.

    :param patient_ids: List of patient IDs to filter data.
    :param output_file: Name of the CSV file to save the output.
    """
    engine = get_db_engine()
    if not engine:
        return None  # Exit if connection fails

    try:
        # Load SQL query from file
        sql_path = importlib.resources.files(sql) / query_file

        with sql_path.open("r") as file:
            sql_template = file.read()

        # Inject dynamic table name safely
        sql_query = sql_template.format(rgs_mode=rgs_mode)

        # Convert patient IDs to a parameterized query
        query_text = text(sql_query)
        params = {"patient_ids": tuple(patient_ids)}

        # Execute the query
        with engine.connect() as connection:
            df = pd.read_sql(query_text, connection, params=params, dtype_backend='numpy_nullable')

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

def fetch_rgs_data(patients_ids, rgs_mode="plus", output_file=None):
    """
    Fetch RGS interaction data for given patient IDs and save it as a CSV file.
    
    :param patients_ids: List of patient IDs to filter data.
    :param rgs_mode: RGS mode to filter data.
    :param output_file: Name of the CSV file to save the

    :return: DataFrame containing the RGS interaction data.
    """
    query_file="query.sql"
    return _fetch_data(patient_ids=patients_ids, rgs_mode=rgs_mode, query_file=query_file, output_file=output_file)

def fetch_timeseries_data(patients_ids, rgs_mode="plus", output_file=None):
    query_file="query_timeseries.sql"
    return _fetch_data(patient_ids=patients_ids, rgs_mode=rgs_mode, query_file=query_file, output_file=output_file)

### ---- Get IDs ---- ####

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

def fetch_patients_by_str(pattern):
    engine = get_db_engine()
    if not engine:
        return None  # Exit if connection fails

    try:
        # Use parameterized queries to avoid '%' format errors
        query = text("""
        SELECT *
        FROM patient
        WHERE PATIENT_USER LIKE :pattern;
        """)

        # Execute query using SQLAlchemy's connection
        with engine.connect() as connection:
            df = pd.read_sql(query, connection, params={"pattern": f"%{pattern}%"})

        patient_ids = df["PATIENT_ID"].tolist()
        return patient_ids, df

    except Exception as e:
        print(f"Query execution failed: {e}")
        return None

    finally:
        engine.dispose()
        print("Database engine closed")

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
