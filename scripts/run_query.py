from pathlib import Path
from recsys_interface.data.interface import fetch_rgs_interaction_data, fetch_patients_in_hospital

rgs_mode = "app"

output_filepath = Path("../data")
output_filename = f"rgs_{rgs_mode}.csv"

hospital_id = [
    7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25
]
patient_ids = fetch_patients_in_hospital(hospital_id)

# Run the function
fetch_rgs_interaction_data(patient_ids, rgs_mode=rgs_mode, output_file=output_filepath / output_filename)
