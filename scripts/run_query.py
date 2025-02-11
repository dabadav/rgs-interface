from pathlib import Path
from recsys_interface.data.interface import fetch_rgs_data, fetch_dms_data, fetch_patients_in_hospital, save_to_csv
import pandas as pd



RGS_MODE = "app"
HOSPITAL_LIST = [
    7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25
]
OUTPUT_PATH = Path("../data")
OUTPUT_RGS = OUTPUT_PATH / f"rgs_{RGS_MODE}.csv"
OUTPUT_DMS = OUTPUT_PATH / f"rgs_dms_{RGS_MODE}.csv"
OUTPUT_TIMESERIES = OUTPUT_PATH / f"rgs_timeseries_{RGS_MODE}.csv"

# Fetch patient IDs in the hospital AND fetch RGS interaction data

# If file does not exist
if not OUTPUT_RGS.exists():
    patient_ids = fetch_patients_in_hospital(HOSPITAL_LIST)
    rgs_data = fetch_rgs_data(patient_ids, rgs_mode=RGS_MODE, output_file=OUTPUT_RGS)

if not OUTPUT_DMS.exists():
    rgs_dms  = fetch_dms_data(rgs_mode=RGS_MODE, output_file=OUTPUT_DMS)

if not OUTPUT_TIMESERIES.exists():
    rgs_data = pd.read_csv(OUTPUT_RGS)
    rgs_dms = pd.read_csv(OUTPUT_DMS)
    rgs_timeseries = rgs_data.merge(rgs_dms, on=["PATIENT_ID","SESSION_ID","PROTOCOL_ID"], how="left")
    save_to_csv(rgs_timeseries, OUTPUT_TIMESERIES)