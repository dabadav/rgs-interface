import pandas as pd
from sqlalchemy import text, exc
import importlib.resources
from rgs_interface import sql
from rgs_interface.db import get_db_engine 

# Exceptions 
class DatabaseOperationError(Exception):
     """Custom exception for database operation failures."""
     pass

class DatabaseQueryError(DatabaseOperationError):
     """Custom exception for query execution failures."""
     pass

class DatabaseWriteError(DatabaseOperationError):
    """Custom exception for write operation failures."""
    pass


class DatabaseInterface:
    def __init__(self):
        """
        Initializes the DatabaseInterface, obtaining a database engine.
        """
        self.engine = get_db_engine()
        if not self.engine:
            print("Critical: Database engine could not be obtained during DatabaseInterface initialization.")

    ###########################
    ### ---- Get Data ---- ####
    ###########################

    def fetch_rgs_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch RGS interaction data for given patient IDs and save it as a CSV file.
        
        :param patients_ids: List of patient IDs to filter data. (Original typo in param name)
        :param rgs_mode: RGS mode to filter data.
        :param output_file: Name of the CSV file to save the

        :return: DataFrame containing the RGS interaction data.
        """
        query_file="query.sql"
        return self._fetch(
            query=query_file,
            params={"patient_ids": tuple(patient_ids)},
            rgs_mode=rgs_mode,
            output_file=output_file
        )

    def fetch_timeseries_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch timeseries RGS interaction data for given patient IDs.
        """
        # Hack as there is no multiindex in across tables
        dm = self.fetch_dm_data(patient_ids, rgs_mode)
        pe = self.fetch_pe_data(patient_ids, rgs_mode)
        

        if dm is None or pe is None:
            print("Error in fetch_timeseries_data: Failed to retrieve dm or pe data.")
            return None 

        return dm.merge(
            pe,
            on=["SESSION_ID", "PATIENT_ID", "PROTOCOL_ID", "GAME_MODE", "SECONDS_FROM_START"],
        )


    def fetch_dm_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch timeseries RGS interaction data for given patient IDs.
        """
        query_file="query_dm.sql"
        return self._fetch(
            query=query_file,
            params={"patient_ids": tuple(patient_ids)},
            rgs_mode=rgs_mode,
            output_file=output_file
        )

    def fetch_pe_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch timeseries RGS interaction data for given patient IDs.
        """
        query_file="query_pe.sql"
        return self._fetch(
            query=query_file,
            params={"patient_ids": tuple(patient_ids)},
            rgs_mode=rgs_mode,
            output_file=output_file
        )

    ### ---- Get IDs ---- ####

    def fetch_patients_by_hospital(self, hospital_ids):
        """
        Fetch list of patient IDs from a given list of hospital IDs.
        """
        if not isinstance(hospital_ids, (list, tuple)):
            hospital_ids = [hospital_ids] # Ensure it's a list/tuple for parameterization

        # The SQL query now uses a named parameter for the IN clause - I know this is not necessary but it is best practice to avoid SQL injections.
        sql_query_string = """
        SELECT PATIENT_ID
        FROM patient
        WHERE HOSPITAL_ID IN :h_ids;
        """
        return self._fetch(
            query=sql_query_string,
            params={"h_ids": tuple(hospital_ids)}
        )

    def fetch_patients_by_name(self, pattern):
        """
        Fetch patient IDs based on a pattern match in the PATIENT_USER field.
        """
        return self._fetch(
            query="SELECT * FROM patient WHERE PATIENT_USER LIKE :pattern;",
            params={"pattern": f"%{pattern}%"}
        )

    def fetch_patients(self):
        return self._fetch(
            query="SELECT * FROM patient"
        )

    ### ---- Handler ---- ####

    def _fetch(self, query, params=None, rgs_mode=None, output_file=None, dtype_backend="numpy_nullable"):
        """
        Generalized function to fetch data from the database using either a SQL file name or a raw query string.

        :param query: SQL file name (string ending with '.sql') OR raw SQL query as a string.
        :param params: Dictionary of parameters to safely format the query.
        :param output_file: CSV file to save the results.
        :param dtype_backend: Backend for pandas DataFrame dtype (default: numpy_nullable).
        
        :return: DataFrame with query results.
        """
        if not self.engine:
            print("Query execution failed: Database engine not available.")
            return None

        try:
            # Accepts SQL file or str
            if query.endswith(".sql"):
                sql_path = importlib.resources.files(sql) / query
                with sql_path.open("r") as file:
                    sql_query = file.read()
            else:
                sql_query = query

            if rgs_mode:
                sql_query = sql_query.format(rgs_mode=rgs_mode)
            
            query_text = text(sql_query)

            # Execute query
            with self.engine.connect() as connection:
                df = pd.read_sql(query_text, connection, params=params, dtype_backend=dtype_backend)

            if output_file:
                df.to_csv(output_file, index=False)
                print(f"Data successfully saved to {output_file}")

            return df

        except Exception as e:
            print(f"Query execution failed: {e}")
            return None


    ### ---- Write Operations ---- ###

    def _execute_write(self, query, params=None): 
        """
        Generalized private method to execute a write operation (INSERT, UPDATE, DELETE).
        Can take a .sql file name or a raw SQL query string. Uses transactions.

        :param query: SQL file name (string ending with '.sql') OR raw SQL query as a string.
        :param params: Dictionary of parameters to safely bind to the query.
        :return: Number of rows affected, or None if an error occurs.
        """
        if not self.engine:
            print("Database write operation failed: Database engine not available.")
            return None

        rows_affected = None
        try:
            if query.endswith(".sql"):
                sql_path = importlib.resources.files(sql) / query
                with sql_path.open("r") as file:
                    sql_query_str = file.read()
            else:
                sql_query_str = query
            
            query_obj = text(sql_query_str) 

            with self.engine.connect() as connection:
                with connection.begin() as transaction: 
                    result = connection.execute(query_obj, parameters=params)
                    if result.is_insert or result.is_update or result.is_delete:
                        rows_affected = result.rowcount
                    transaction.commit()
                print(f"Write operation successful. Rows affected: {rows_affected}")
            return rows_affected
        except FileNotFoundError: # Specific exception for missing .sql file
            print(f"Database write operation failed: SQL file '{query}' not found.")
            return None
        except exc.SQLAlchemyError as e: # More specific SQLAlchemy error
            print(f"Database write operation failed (SQLAlchemyError): {e}")
            return None
        except Exception as e: # Catch other potential errors
            print(f"Database write operation failed (General Exception): {e}")
            return None


    def close(self):
        """
        Disposes of the database engine and its connection pool.
        This should be called when the DatabaseInterface object is no longer needed.
        """
        if self.engine:
            self.engine.dispose()
            print("Database engine closed")
            self.engine = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()