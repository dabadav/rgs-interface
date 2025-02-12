# RGS Data Fetching Script

This script fetches Rehabilitation Gaming System (RGS) data for patients based on either a list of patient IDs or hospital IDs. It allows flexible input handling via command-line arguments or a text file.

## Features
- Fetch patient data by specifying either patient IDs or hospital IDs.
- Read patient IDs from a text file.
- Save the output data as CSV files.
- Command-line interface for flexibility.

## Requirements
Ensure you have Python installed and the required dependencies:
```sh
pip install pandas pathlib argparse recsys_interface
```

## Usage
Run the script using one of the following methods:

### 1. Fetch Data for Specific Patients
You can provide patient IDs directly:
```sh
fetch-rgs --mode patients --patients 204 775 787 788
```

Or, provide a text file where each line contains a patient ID:
```sh
fetch-rgs --mode patients --patients-file patient_ids.txt
```

### 2. Fetch Data for Patients in Hospitals
Provide hospital IDs to fetch all associated patient IDs:
```sh
fetch-rgs --mode hospital --hospital 7 8 9 11 12
```

### 3. Set RGS Mode (Optional)
You can change the RGS mode (default is `app`) using the `--rgs-mode` flag:
```sh
fetch-rgs --mode patients --patients 204 775 --rgs-mode plus
```

### 3. Set RGS Mode (Optional)
You can change the RGS mode (default is `app`) using the `--rgs-mode` flag:
```sh
fetch-rgs --mode patients --patients 204 775 --rgs-mode plus
```

## Script Logic
- **Mode Selection:**
  - `patients`: Fetches data based on patient IDs.
  - `hospital`: Fetches patient IDs from hospital IDs.
- **Patient ID Input:**
  - Directly via `--patients`.
  - From a file via `--patients-file`.
- **Output Files:**
  - `rgs_<mode>.csv`
  - Custom: Specified via `--output-file`
- **DMS Timeseries Data:**
  - `--dms True` includes DMs timeseries data.
  - Default: `False` (DMs data not included).

## Example Output
If run with:
```sh
fetch-rgs --mode patients --patients 204 775 --dms True --output-file my_output.csv
```
Output files will be:
```
my_output.csv
```