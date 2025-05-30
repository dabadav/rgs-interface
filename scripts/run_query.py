import sys
sys.path.append("..")

from pathlib import Path
from recsys_interface.data.interface import DatabaseInterface
from datetime import datetime, date

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
OUTPUT_RGS = OUTPUT_PATH / f"rgs_{RGS_MODE}_{date.today()}.csv"

# Run code
print("Running...")
patient_ids = PATIENT_LIST
db_handler = DatabaseInterface()
# rgs_data = db_handler.fetch_rgs_data(patient_ids, rgs_mode=RGS_MODE, output_file=OUTPUT_RGS)
dms_data = db_handler.fetch_timeseries_data(patient_ids, rgs_mode="app")