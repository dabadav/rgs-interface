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
                DATE(ea.CREATION_TIME) AS ANSWER_DATE,
                ea.EMOTIONAL_ANSWER,
                ea.CREATION_TIME,
                ROW_NUMBER() OVER (PARTITION BY eqp.PATIENT_ID, DATE(ea.CREATION_TIME) ORDER BY ea.EMOTIONAL_ANSWER_ID) AS answer_rank
            FROM emotional_question_patient eqp
            JOIN emotional_answer ea
                ON eqp.EMOTIONAL_QUESTION_PATIENT_ID = ea.EMOTIONAL_QUESTION_PATIENT_ID
        ),

        SessionData AS (
            SELECT
                pp.PATIENT_ID,
                sp.SESSION_ID,
                sp.PRESCRIPTION_ID,
                pp.PROTOCOL_ID,
                prt.PROTOCOL_TYPE,
                pp.WEEKDAY,
                pp.SESSION_DURATION AS PRESCRIBED_SESSION_DURATION,
                pp.AR_MODE,
                DATE(sp.STARTING_DATE) AS SESSION_DATE,
                sp.STARTING_DATE,
                sp.ENDING_DATE,
                sp.STATUS,
                sp.PLATFORM,
                sp.DEVICE
            FROM session_plus sp
            JOIN prescription_plus pp
                ON sp.PRESCRIPTION_ID = pp.PRESCRIPTION_ID
            JOIN protocol as pr
                ON pp.PROTOCOL_ID = pr.PROTOCOL_ID
            JOIN protocol_type as prt
                ON pr.PROTOCOL_TYPE_ID = prt.PROTOCOL_TYPE_ID
            WHERE sp.STATUS IN ('CLOSED', 'ABORTED')  -- Filters only CLOSED sessions, WHERE sp.STATUS = 'CLOSED' vs WHERE sp.STATUS IN ('CLOSED', 'ABORTED') for all sessions
        )

        SELECT
            p.PATIENT_ID,
            -- p.HOSPITAL_ID,
            p.PATIENT_USER,
            -- p.CREATION_TIME AS PATIENT_CREATION_TIME,
            -- p.DELETE_TIME,
            -- p.NAME,
            -- p.SURNAME1,
            -- p.SURNAME2,
            p.PARETIC_SIDE,
            p.UPPER_EXTREMITY_TO_TRAIN,
            p.HAND_RAISING_CAPACITY,
            p.COGNITIVE_FUNCTION_LEVEL,
            p.HAS_HEMINEGLIGENCE,
            p.GENDER,
            p.SKIN_COLOR,
            -- p.BIRTH_DATE,
            TIMESTAMPDIFF(YEAR, p.BIRTH_DATE, sd.SESSION_DATE) AS AGE, -- Age at session time
            p.VIDEOGAME_EXP,
            p.COMPUTER_EXP,
            p.COMMENTS,
            p.PTN_HEIGHT_CM,
            p.ARM_SIZE_CM,
            -- p.DEMO,
            -- p.VERSION,

            sd.SESSION_ID,
            HOUR(sd.STARTING_DATE) AS STARTING_HOUR,
            CASE
                WHEN sd.STARTING_DATE IS NULL THEN NULL
                WHEN HOUR(sd.STARTING_DATE) BETWEEN 5 AND 11 THEN 'MORNING'
                WHEN HOUR(sd.STARTING_DATE) BETWEEN 12 AND 17 THEN 'AFTERNOON'
                WHEN HOUR(sd.STARTING_DATE) BETWEEN 18 AND 21 THEN 'EVENING'
                ELSE 'NIGHT'
            END AS STARTING_TIME_CATEGORY,
            -- sd.ENDING_DATE,
            sd.STATUS,
            sd.PLATFORM,
            sd.DEVICE,
            CAST(sd.PROTOCOL_ID AS SIGNED) AS PROTOCOL_ID, -- Ensures integer format
            sd.PROTOCOL_TYPE,
            sd.AR_MODE,
            sd.WEEKDAY,
            sd.PRESCRIBED_SESSION_DURATION,
            r.SESSION_DURATION,

            CASE
                WHEN sd.PRESCRIBED_SESSION_DURATION > 0 THEN r.SESSION_DURATION / sd.PRESCRIBED_SESSION_DURATION
                ELSE NULL
            END AS ADHERENCE,

            r.TOTAL_SUCCESS,
            r.TOTAL_ERRORS,
            r.SCORE,

            ea1.EMOTIONAL_ANSWER AS EMOTIONAL_ANSWER_1,
            ea2.EMOTIONAL_ANSWER AS EMOTIONAL_ANSWER_2,
            ea3.EMOTIONAL_ANSWER AS EMOTIONAL_ANSWER_3
            -- ea1.CREATION_TIME AS EMOTIONAL_ANSWER_CREATION_TIME

        FROM patient p

        LEFT JOIN SessionData sd
            ON p.PATIENT_ID = sd.PATIENT_ID

        LEFT JOIN (
            SELECT
                SESSION_ID,
                MAX(CASE WHEN RECORDING_KEY = 'sessionDuration(seconds)' THEN RECORDING_VALUE END) AS SESSION_DURATION,
                MAX(CASE WHEN RECORDING_KEY = 'totalSuccess' THEN RECORDING_VALUE END) AS TOTAL_SUCCESS,
                MAX(CASE WHEN RECORDING_KEY = 'totalErrors' THEN RECORDING_VALUE END) AS TOTAL_ERRORS,
                MAX(CASE WHEN RECORDING_KEY = 'score' THEN RECORDING_VALUE END) AS SCORE
            FROM recording_plus
            GROUP BY SESSION_ID
        ) r
            ON sd.SESSION_ID = r.SESSION_ID

        LEFT JOIN (
            SELECT PATIENT_ID, ANSWER_DATE, EMOTIONAL_ANSWER, CREATION_TIME
            FROM EmotionalAnswers
            WHERE answer_rank = 1
        ) ea1 ON p.PATIENT_ID = ea1.PATIENT_ID AND sd.SESSION_DATE = ea1.ANSWER_DATE

        LEFT JOIN (
            SELECT PATIENT_ID, ANSWER_DATE, EMOTIONAL_ANSWER
            FROM EmotionalAnswers
            WHERE answer_rank = 2
        ) ea2 ON p.PATIENT_ID = ea2.PATIENT_ID AND sd.SESSION_DATE = ea2.ANSWER_DATE

        LEFT JOIN (
            SELECT PATIENT_ID, ANSWER_DATE, EMOTIONAL_ANSWER
            FROM EmotionalAnswers
            WHERE answer_rank = 3
        ) ea3 ON p.PATIENT_ID = ea3.PATIENT_ID AND sd.SESSION_DATE = ea3.ANSWER_DATE

        WHERE p.PATIENT_ID IN ({patient_id_str})
        ORDER BY p.PATIENT_ID, sd.SESSION_DATE;
        """

        df = pd.read_sql(query, engine)
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
    # patient_ids = [3588]
    # patient_ids = [1508]

    patient_ids = [
        1347, 1348, 1349, 1454, 1455, 1456, 1457, 1458, 1459, 1460, 1477,
        1478, 1479, 1480, 1481, 1482, 1484, 2332, 2333, 2334, 2335, 2336,
        2422, 2423, 2569, 2607, 2628, 2659, 2660, 2661, 2662, 2861, 2862,
        2864, 2865, 2866, 2882, 2886, 2897, 2930, 2947, 2967, 3026, 3084,
        3085, 3086, 3088, 3089, 3096, 3097, 3163, 3167, 3168, 3316, 3322
    ]

    data = fetch_rgs_interaction_data(patient_ids)
