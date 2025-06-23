# %%
import importlib.resources
import logging
from typing import Union

import pandas as pd
from rgs_interface import sql
from rgs_interface.data.schemas import PrescriptionStagingRow, RecsysMetricsRow
from rgs_interface.db import get_db_engine
from sqlalchemy import exc, text

logger = logging.getLogger(__name__)


class DatabaseInterface:
    def __init__(self):
        """
        Initializes the DatabaseInterface, obtaining a database engine.
        """
        self.engine = get_db_engine()
        if not self.engine:
            logger.critical(
                "Database engine could not be obtained during DatabaseInterface initialization."
            )

    ###########################
    ### ---- Get Data ---- ####
    ###########################

    def fetch_rgs_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch RGS interaction data for given patient IDs and save it as a CSV file.

        :param patients_ids: List of patient IDs to filter data. (Original typo in param name)
        :param rgs_mode: RGS mode to filter data.
        :param output_file: Name of the CSV file to save th
        :return: DataFrame containing the RGS interaction data.
        """

        query_file = "query.sql"
        return self._fetch(
            query=query_file,
            params={"patient_ids": tuple(patient_ids)},
            rgs_mode=rgs_mode,
            output_file=output_file,
        )

    def fetch_timeseries_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch timeseries RGS interaction data for given patient IDs.
        """
        # Hack as there is no multiindex in across tables
        dm = self.fetch_dm_data(patient_ids, rgs_mode)
        pe = self.fetch_pe_data(patient_ids, rgs_mode)

        if dm.empty or pe.empty:
            logger.error("Failed to retrieve DM or PE data in fetch_timeseries_data().")
            return None

        return dm.merge(
            pe,
            on=[
                "SESSION_ID",
                "PATIENT_ID",
                "PROTOCOL_ID",
                "GAME_MODE",
                "SECONDS_FROM_START",
            ],
        )

    def fetch_dm_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch timeseries RGS interaction data for given patient IDs.
        """
        query_file = "query_dm.sql"
        return self._fetch(
            query=query_file,
            params={"patient_ids": tuple(patient_ids)},
            rgs_mode=rgs_mode,
            output_file=output_file,
        )

    def fetch_clinical_data(self, patient_ids, output_file=None):
        """
        Fetch clinical data for given patient IDs, from the `clinical_trials` table.

        The expected structure of the `clinical_trials` table is:
        - PATIENT_ID: Unique identifier for the patient.
        - STUDY_ID: Identifier for the clinical study.
        - CLINICAL_SCORES: Clinical scores associated with the patient.
        - RECOMMEND: Boolean indicating if the patient is recommended for the study.

        The json containing clinical scores is expected to have the following structure:
        - Support mutliple evaluations per patient as keys.
        - Each evaluation contains:
        - evaluation_date: Date of the evaluation.
        - condition: Condition of the patient at the time of evaluation (e.g., "pre", "post").

        .. code-block:: json
        [
            {
                "evaluation_date": "2023-12-04",
                "condition": "pre",
                "MoCA": {
                    "Visuospatial/Executive": 0,
                    "Naming": 3,
                    "Attention": 5,
                    "Language": 0,
                    "Abstraction": 0,
                    "Delayed Recall": 2,
                    "Orientation": 6
                },
                "Fugl-Meyer": {
                    "FM_A": 8,
                    "FM_B": 18,
                    "FM_C": 2,
                    "FM_D": 7
                }
            }
        ]
        """
        sql_query_string = """
        SELECT *
        FROM `clinical_trials`
        WHERE `PATIENT_ID` IN :patient_ids;
        """
        return self._fetch(
            query=sql_query_string, params={"patient_ids": tuple(patient_ids)}
        )

    def fetch_pe_data(self, patient_ids, rgs_mode="plus", output_file=None):
        """
        Fetch timeseries RGS interaction data for given patient IDs.
        """
        query_file = "query_pe.sql"
        return self._fetch(
            query=query_file,
            params={"patient_ids": tuple(patient_ids)},
            rgs_mode=rgs_mode,
            output_file=output_file,
        )

    ### ---- Get IDs ---- ####

    def fetch_patients_by_hospital(self, hospital_ids):
        """
        Fetch list of patient IDs from a given list of hospital IDs.
        """
        if not isinstance(hospital_ids, (list, tuple)):
            hospital_ids = [hospital_ids]

        sql_query_string = """
        SELECT PATIENT_ID
        FROM patient
        WHERE HOSPITAL_ID IN :h_ids;
        """
        return self._fetch(
            query=sql_query_string, params={"h_ids": tuple(hospital_ids)}
        )

    def fetch_patients_by_name(self, pattern):
        """
        Fetch patient IDs based on a pattern match in the PATIENT_USER field.
        """
        return self._fetch(
            query="SELECT * FROM patient WHERE PATIENT_USER LIKE :pattern;",
            params={"pattern": f"%{pattern}%"},
        )

    def fetch_patients_by_study(self, study_ids):
        """
        Fetch patient IDs based on which study
        """
        return self._fetch(
            query="SELECT * FROM `clinical_trials` WHERE `STUDY_ID` = :study_id AND `RECOMMEND` = 1;",
            params={"study_id": tuple(study_ids)},
        )

    def fetch_patients(self):
        return self._fetch(query="SELECT * FROM patient")

    ### ---- Read Handler ---- ####

    def _fetch(
        self,
        query,
        params=None,
        rgs_mode=None,
        output_file=None,
        dtype_backend="numpy_nullable",
    ):
        """
        Generalized function to fetch data from the database using either a SQL file name or a raw query string
        :param query: SQL file name (string ending with '.sql') OR raw SQL query as a string.
        :param params: Dictionary of parameters to safely format the query.
        :param output_file: CSV file to save the results.
        :param dtype_backend: Backend for pandas DataFrame dtype (default: numpy_nullable).

        :return: DataFrame with query results.
        """
        if not self.engine:
            logger.error("Query execution failed: Database engine not available.")
            return None

        try:
            if query.endswith(".sql"):
                sql_path = importlib.resources.files(sql) / query
                with sql_path.open("r") as file:
                    sql_query = file.read()
            else:
                sql_query = query

            if rgs_mode:
                sql_query = sql_query.format(rgs_mode=rgs_mode)

            query_text = text(sql_query)
            with self.engine.connect() as connection:
                df = pd.read_sql(
                    query_text, connection, params=params, dtype_backend=dtype_backend
                )

            if output_file:
                df.to_csv(output_file, index=False)
                logger.info("Data successfully saved to %s", output_file)
            return df
        except Exception as e:
            logger.exception("Query execution failed with exception.")
            return None

    ### ---- Write Operations ---- ###

    def add_prescription_staging_entry(
        self, entry: PrescriptionStagingRow
    ) -> Union[int, None]:
        """
        Adds a new entry to the prescription_staging table and returns the new ID.
        """
        if not isinstance(entry, PrescriptionStagingRow):
            logger.error("Error: entry must be an instance of PrescriptionStagingRow.")
            return None

        sql_query = """
        INSERT INTO prescription_staging (
            PRESCRIPTION_STAGING_ID, PATIENT_ID, PROTOCOL_ID, STARTING_DATE, ENDING_DATE, WEEKDAY,
            SESSION_DURATION, RECOMMENDATION_ID, WEEKS_SINCE_START, STATUS
        ) VALUES (
            NULL, :patient_id, :protocol_id, :starting_date, :ending_date, :weekday,
            :session_duration, :recommendation_id, :weeks_since_start, :status
        )
        """
        if not self.engine:
            logger.error(
                "Cannot add prescription staging entry: Database engine not available."
            )
            return None

        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id

        except (TypeError, ValueError) as ve:
            logger.error(f"Data validation error for prescription staging entry: {ve}")
            return None
        except exc.SQLAlchemyError as e:
            logger.error(
                f"Failed to add prescription staging entry (SQLAlchemyError): {e}"
            )
            return None
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while adding prescription staging entry."
            )
            return None

    def add_recsys_metric_entry(self, entry: RecsysMetricsRow) -> Union[int, None]:
        """
        Adds a new entry to the recsys_metrics table and returns the new ID.
        """
        if not isinstance(entry, RecsysMetricsRow):
            logger.error("Error: entry must be an instance of RecsysMetricsRow.")
            return None

        sql_query = """
       INSERT INTO recsys_metrics (
            RECSYS_METRICS_ID, PATIENT_ID, PROTOCOL_ID, RECOMMENDATION_ID, METRIC_DATE, METRIC_KEY, METRIC_VALUE
        ) VALUES (
            NULL, :patient_id, :protocol_id, :recommendation_id, :metric_date, :metric_key, :metric_value
        )
        """
        if not self.engine:
            logger.error(
                "Cannot add recsys metric entry: Database engine not available."
            )
            return None

        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id

        except (TypeError, ValueError) as ve:
            logger.error(f"Data validation error for recsys metric entry: {ve}")
            return None
        except exc.SQLAlchemyError as e:
            logger.error(f"Failed to add recsys metric entry (SQLAlchemyError): {e}")
            return None
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while adding recsys metric entry."
            )
            return None

    def add_clinical_trials_entry(self, entry: ClinicalTrialsRow) -> Union[int, None]:
        """
        Adds a new entry to the clinical_trials table and returns the new ID.
        """
        if not isinstance(entry, ClinicalTrialsRow):
            print("Error: entry must be an instance of ClinicalTrialsRow.")
            return None
        sql_query = """
        INSERT INTO clinical_trials(
            CLINICAL_TRIALS_ID, PATIENT_ID, STUDY_ID, STUDY_NAME, START_DATE, END_DATE, CLINICAL_SCORES, RECOMMEND
        ) VALUES (
            :clinical_trials_id, :patient_id, :study_id, :study_name, :start_date, :end_date, :clinical_scores, :recommend
        )
        """
        if not self.engine:
            print("Cannot add clinical_trials entry: Database engine not available.")
            return None
        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id
        except Exception as e:
            print(f"Failed to add clinical_trials entry: {e}")
            return None

    def add_patient_entry(self, entry: PatientRow) -> Union[int, None]:
        """
        Adds a new entry to the patient table and returns the new ID.
        """
        if not isinstance(entry, PatientRow):
            print("Error: entry must be an instance of PatientRow.")
            return None
        sql_query = """
        INSERT INTO patient(
            PATIENT_ID, HOSPITAL_ID, PATIENT_USER, PASSWORD, CREATION_TIME, DELETE_TIME, NAME, SURNAME1, SURNAME2, EMAIL, PARETIC_SIDE, UPPER_EXTREMITY_TO_TRAIN, HAND_RAISING_CAPACITY, COGNITIVE_FUNCTION_LEVEL, HAS_HEMINEGLIGENCE, GENDER, SKIN_COLOR, BIRTH_DATE, VIDEOGAME_EXP, COMPUTER_EXP, COMMENTS, PTN_HEIGHT_CM, ARM_SIZE_CM, DEMO, VERSION, HAS_RECOMMENDER_SYSTEM
        ) VALUES (
            :patient_id, :hospital_id, :patient_user, :password, :creation_time, :delete_time, :name, :surname1, :surname2, :email, :paretic_side, :upper_extremity_to_train, :hand_raising_capacity, :cognitive_function_level, :has_heminegligence, :gender, :skin_color, :birth_date, :videogame_exp, :computer_exp, :comments, :ptn_height_cm, :arm_size_cm, :demo, :version, :has_recommender_system
        )
        """
        if not self.engine:
            print("Cannot add patient entry: Database engine not available.")
            return None
        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id
        except Exception as e:
            print(f"Failed to add patient entry: {e}")
            return None

    def add_difficulty_modulators_plus_entry(
        self, entry: DifficultyModulatorsPlusRow
    ) -> Union[int, None]:
        """
        Adds a new entry to the difficulty_modulators_plus table and returns the new ID.
        """
        if not isinstance(entry, DifficultyModulatorsPlusRow):
            print("Error: entry must be an instance of DifficultyModulatorsPlusRow.")
            return None
        sql_query = """
        INSERT INTO difficulty_modulators_plus(
            DIFFICULTY_MODULATORS_ID, SESSION_ID, PATIENT_ID, PROTOCOL_ID, GAME_MODE, SECONDS_FROM_START, PARAMETER_KEY, PARAMETER_VALUE
        ) VALUES (
            :difficulty_modulators_id, :session_id, :patient_id, :protocol_id, :game_mode, :seconds_from_start, :parameter_key, :parameter_value
        )
        """
        if not self.engine:
            print(
                "Cannot add difficulty_modulators_plus entry: Database engine not available."
            )
            return None
        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id
        except Exception as e:
            print(f"Failed to add difficulty_modulators_plus entry: {e}")
            return None

    def add_performance_estimators_plus_entry(
        self, entry: PerformanceEstimatorsPlusRow
    ) -> Union[int, None]:
        """
        Adds a new entry to the performance_estimators_plus table and returns the new ID.
        """
        if not isinstance(entry, PerformanceEstimatorsPlusRow):
            print("Error: entry must be an instance of PerformanceEstimatorsPlusRow.")
            return None
        sql_query = """
        INSERT INTO performance_estimators_plus(
            PERFORMANCE_ESTIMATORS_ID, SESSION_ID, PATIENT_ID, PROTOCOL_ID, GAME_MODE, SECONDS_FROM_START, PARAMETER_KEY, PARAMETER_VALUE
        ) VALUES (
            :performance_estimators_id, :session_id, :patient_id, :protocol_id, :game_mode, :seconds_from_start, :parameter_key, :parameter_value
        )
        """
        if not self.engine:
            print(
                "Cannot add performance_estimators_plus entry: Database engine not available."
            )
            return None
        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id
        except Exception as e:
            print(f"Failed to add performance_estimators_plus entry: {e}")
            return None

    def add_session_plus_entry(self, entry: SessionPlusRow) -> Union[int, None]:
        """
        Adds a new entry to the session_plus table and returns the new ID.
        """
        if not isinstance(entry, SessionPlusRow):
            print("Error: entry must be an instance of SessionPlusRow.")
            return None
        sql_query = """
        INSERT INTO session_plus(
            SESSION_ID, PRESCRIPTION_ID, STARTING_DATE, ENDING_DATE, STATUS, PLATFORM, DEVICE, SESSION_LOG_PARSED
        ) VALUES (
            :session_id, :prescription_id, :starting_date, :ending_date, :status, :platform, :device, :session_log_parsed
        )
        """
        if not self.engine:
            print("Cannot add session_plus entry: Database engine not available.")
            return None
        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id
        except Exception as e:
            print(f"Failed to add session_plus entry: {e}")
            return None

    def add_prescription_plus_entry(
        self, entry: PrescriptionPlusRow
    ) -> Union[int, None]:
        """
        Adds a new entry to the prescription_plus table and returns the new ID.
        """
        if not isinstance(entry, PrescriptionPlusRow):
            print("Error: entry must be an instance of PrescriptionPlusRow.")
            return None
        sql_query = """
        INSERT INTO prescription_plus(
            PRESCRIPTION_ID, PATIENT_ID, PROTOCOL_ID, STARTING_DATE, ENDING_DATE, WEEKDAY, SESSION_DURATION, AR_MODE
        ) VALUES (
            :prescription_id, :patient_id, :protocol_id, :starting_date, :ending_date, :weekday, :session_duration, :ar_mode
        )
        """
        if not self.engine:
            print("Cannot add prescription_plus entry: Database engine not available.")
            return None
        new_id = None
        try:
            params = entry.to_params_dict()
            with self.engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query), parameters=params)
                    if result.rowcount == 1:
                        new_id = result.lastrowid
                    transaction.commit()
            return new_id
        except Exception as e:
            print(f"Failed to add prescription_plus entry: {e}")
            return None

    def fetch_recsys_metrics(self, patient_id=None):
        """
        Fetch recsys_metrics entries, optionally filtered by patient_id.
        """
        query = "SELECT * FROM recsys_metrics"
        params = None
        if patient_id is not None:
            query += " WHERE PATIENT_ID = :patient_id"
            params = {"patient_id": patient_id}
        return self._fetch(query=query, params=params)

    def fetch_prescription_staging(self, patient_id=None):
        """
        Fetch prescription_staging entries, optionally filtered by patient_id.
        """
        query = "SELECT * FROM prescription_staging"
        params = None
        if patient_id is not None:
            query += " WHERE PATIENT_ID = :patient_id"
            params = {"patient_id": patient_id}
        return self._fetch(query=query, params=params)

    ### ---- Write Handler ---- ####
    def _execute_write(self, query, params=None):
        """
        Generalized private method to execute a write operation (INSERT, UPDATE, DELETE).
        Can take a .sql file name or a raw SQL query string. Uses transactions
        :param query: SQL file name (string ending with '.sql') OR raw SQL query as a string.
        :param params: Dictionary of parameters to safely bind to the query.
        :return: Number of rows affected, or None if an error occurs.
        """
        if not self.engine:
            logger.error(
                "Database write operation failed: Database engine not available."
            )
            return None

        rows_affected = None
        sql_query_str = ""
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
                logger.info(
                    f"Write operation successful. Rows affected: {rows_affected}"
                )
            return rows_affected
        except FileNotFoundError:
            logger.error(
                f"Database write operation failed: SQL file '{query}' not found."
            )
            return None
        except exc.SQLAlchemyError as e:
            logger.error(
                f"Database write operation failed (SQLAlchemyError) for query '{sql_query_str[:100]}...': {e}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"Database write operation failed (General Exception) for query '{sql_query_str[:100]}...': {e}"
            )
            return None

    def close(self):
        """
        Disposes of the database engine and its connection pool.
        This should be called when the DatabaseInterface object is no longer needed.
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine closed")
            self.engine = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
