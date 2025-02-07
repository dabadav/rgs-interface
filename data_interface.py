import pandas as pd
from sqlalchemy import create_engine

def get_db_engine():
    """Create and return a SQLAlchemy engine for MySQL."""
    try:
        engine = create_engine(
            "mysql+pymysql://db_readOnly_prod:REDACTED@rgsweb.eodyne.com/global_prod"
        )
        print("Database engine created successfully")
        return engine
    except Exception as e:
        print(f"Database engine creation failed: {e}")
        return None

def fetch_rgs_interaction_data(patient_ids, output_file="rgs_interactions.csv"):
    """
    Fetch RGS interaction data for given patient IDs and save it as a CSV file.

    :param patient_ids: List of patient IDs to filter data.
    :param output_file: Name of the CSV file to save the output.
    """
    engine = get_db_engine()
    if not engine:
        return None  # Exit if connection fails

    try:
        patient_id_str = ','.join(map(str, patient_ids))

        query = f"""
        WITH EmotionalAnswers AS (
            SELECT
                eqp.PATIENT_ID,
                eqp.EMOTIONAL_QUESTION_PATIENT_ID,
                ea.EMOTIONAL_ANSWER,
                ea.CREATION_TIME,
                ROW_NUMBER() OVER (PARTITION BY eqp.PATIENT_ID, ea.CREATION_TIME ORDER BY ea.EMOTIONAL_ANSWER_ID) AS answer_rank
            FROM emotional_question_patient eqp
            JOIN emotional_answer ea ON eqp.EMOTIONAL_QUESTION_PATIENT_ID = ea.EMOTIONAL_QUESTION_PATIENT_ID
        )

        SELECT
            p.PATIENT_ID,
            p.HOSPITAL_ID,
            p.PATIENT_USER,
            p.CREATION_TIME AS PATIENT_CREATION_TIME,
            p.PARETIC_SIDE,
            p.UPPER_EXTREMITY_TO_TRAIN,
            p.HAND_RAISING_CAPACITY,
            p.COGNITIVE_FUNCTION_LEVEL,
            p.HAS_HEMINEGLIGENCE,
            p.GENDER,
            p.SKIN_COLOR,
            p.BIRTH_DATE,
            p.VIDEOGAME_EXP,
            p.COMPUTER_EXP,
            p.COMMENTS,
            p.PTN_HEIGHT_CM,
            p.ARM_SIZE_CM,

            ea1.CREATION_TIME AS EMOTIONAL_ANSWER_CREATION_TIME,

            -- Emotional answers in a single row (wide format)
            ea1.EMOTIONAL_ANSWER AS EMOTIONAL_ANSWER_1,
            ea2.EMOTIONAL_ANSWER AS EMOTIONAL_ANSWER_2,
            ea3.EMOTIONAL_ANSWER AS EMOTIONAL_ANSWER_3

        FROM patient p

        LEFT JOIN (
            SELECT PATIENT_ID, EMOTIONAL_ANSWER, CREATION_TIME
            FROM EmotionalAnswers
            WHERE answer_rank = 1
        ) ea1 ON p.PATIENT_ID = ea1.PATIENT_ID

        LEFT JOIN (
            SELECT PATIENT_ID, EMOTIONAL_ANSWER, CREATION_TIME
            FROM EmotionalAnswers
            WHERE answer_rank = 2
        ) ea2 ON p.PATIENT_ID = ea2.PATIENT_ID AND ea1.CREATION_TIME = ea2.CREATION_TIME

        LEFT JOIN (
            SELECT PATIENT_ID, EMOTIONAL_ANSWER, CREATION_TIME
            FROM EmotionalAnswers
            WHERE answer_rank = 3
        ) ea3 ON p.PATIENT_ID = ea3.PATIENT_ID AND ea1.CREATION_TIME = ea3.CREATION_TIME

        WHERE p.PATIENT_ID IN ({patient_id_str})
        ORDER BY p.PATIENT_ID, ea1.CREATION_TIME;
        """

        df = pd.read_sql(query, engine)  # Use SQLAlchemy engine
        df.to_csv(output_file, index=False)
        print(f"Data successfully saved to {output_file}")

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

# Test the function
if __name__ == '__main__':
    patient_ids = [3588]
    data = fetch_rgs_interaction_data(patient_ids)
