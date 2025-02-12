from pathlib import Path
from recsys_interface.data.interface import fetch_rgs_data, fetch_dms_data, fetch_patients_in_hospital, save_to_csv
import pandas as pd

RGS_MODE = "app"
HOSPITAL_LIST = [
    7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25
]
PATIENT_LIST = [
    204, 775, 787, 788, 946, 947, 953, 955, 957, 1123, 1169, 1170, 1171,
    1172, 1173, 1222, 1551, 1553, 1555, 1556, 1861, 1983, 2110, 2195, 2843,
    2913, 2925, 2926, 2937, 2954, 2955, 2956, 2957, 2958, 2959, 2960, 2961,
    2962, 2963, 3081, 3210, 3213, 3222, 3229, 3231, 3318, 3432
]
OUTPUT_PATH = Path("../data")
OUTPUT_RGS = OUTPUT_PATH / f"rgs_{RGS_MODE}_raj.csv"
OUTPUT_DMS = OUTPUT_PATH / f"rgs_dms_{RGS_MODE}_raj.csv"
OUTPUT_TIMESERIES = OUTPUT_PATH / f"rgs_timeseries_{RGS_MODE}.csv"

# Run code
patient_ids = PATIENT_LIST
rgs_data = fetch_rgs_data(patient_ids, rgs_mode=RGS_MODE, output_file=OUTPUT_RGS)