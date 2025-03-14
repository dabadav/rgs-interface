## RGS Data Interface

This package provides a python and command-line interface to fetch Rehabilitation Gaming System (RGS) data for patients.

### Installation

```sh
pip install recsys_interface-0.2.0.tar.gz
```

### 📖 Python Module Usage

#### 📦 Main methods `rgs_interface.data.interface`

Method Name               | Description |
|---------------------------|-------------|
| `fetch_rgs_data()`       | Retrieves RGS data for a list of patient IDs. |
| `fetch_timeseries_data()` | Retrieves time-series RGS data for specified patient IDs. |
| `fetch_patients()`       | Retrieves all patient records from the database. |
| `fetch_patients_by_hospital()` | Retrieves patient IDs based on a list of hospital IDs. |
| `fetch_patients_by_name()` | Retrieves patient IDs based on a pattern match in the `PATIENT_USER` field using SQL `LIKE`. |

<details>
  <summary>🔹 Fetching RGS Data</summary>

##### `fetch_rgs_data(patient_ids, rgs_mode="plus", output_file=None)`
- Retrieves RGS interaction data for a list of patient IDs.
- Allows filtering based on `rgs_mode` (default: `"plus"`).
- Saves the results as a CSV file if `output_file` is specified.

**Example Usage:**
```python
df = fetch_rgs_data([101, 102, 103], rgs_mode="app", output_file="rgs_data.csv")
print(df.head())
```

**Example Output (`df.head()`)**:

| PATIENT_ID | HOSPITAL_ID | PARETIC_SIDE | UPPER_EXTREMITY_TO_TRAIN | HAND_RAISING_CAPACITY | COGNITIVE_FUNCTION_LEVEL | HAS_HEMINEGLIGENCE | GENDER  | SKIN_COLOR | AGE  | VIDEOGAME_EXP | COMPUTER_EXP | COMMENTS | PTN_HEIGHT_CM | ARM_SIZE_CM | PRESCRIPTION_ID | SESSION_ID | PROTOCOL_ID | PRESCRIPTION_STARTING_DATE | PRESCRIPTION_ENDING_DATE | SESSION_DATE | STARTING_HOUR | STARTING_TIME_CATEGORY | STATUS  | PROTOCOL_TYPE | AR_MODE | WEEKDAY | REAL_SESSION_DURATION | PRESCRIBED_SESSION_DURATION | SESSION_DURATION | ADHERENCE | TOTAL_SUCCESS | TOTAL_ERRORS | SCORE |
|------------|------------|--------------|---------------------------|------------------------|--------------------------|--------------------|---------|------------|------|---------------|--------------|----------|--------------|------------|----------------|------------|-------------|-------------------------|-------------------------|--------------|--------------|----------------------|---------|--------------|--------|---------|---------------------|-------------------------|----------------|-----------|--------------|-------------|-------|
| 775        | 40         | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165          | 22         | 78256.0        | 16796.0    | 222.0       | 2024-03-28 08:55:00     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0         | AFTERNOON            | CLOSED  | Hands        | NONE   | FRIDAY  | 492.0               | 300.0                   | 300            | 1.0       | 99           | 8           | 231   |
| 775        | 40         | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165          | 22         | 78258.0        | 16798.0    | 224.0       | 2024-03-28 08:55:11     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0         | AFTERNOON            | CLOSED  | Hands        | NONE   | FRIDAY  | 338.0               | 300.0                   | 300            | 1.0       | 64           | 17          | 88    |
| 775        | 40         | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165          | 22         | 78260.0        | 16800.0    | 206.0       | 2024-03-28 08:55:57     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0         | AFTERNOON            | CLOSED  | AR           | TABLE  | FRIDAY  | 280.0               | 240.0                   | 240            | 1.0       | 0            | 0           | 0     |
| 775        | 40         | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165          | 22         | 78262.0        | 16802.0    | 209.0       | 2024-03-28 08:58:19     | 2024-04-15 15:43:10     | 2024-03-29   | 13.0         | AFTERNOON            | CLOSED  | AR           | TABLE  | FRIDAY  | 391.0               | 300.0                   | 300            | 1.0       | 1            | 2           | 1     |

---

#### `fetch_timeseries_data(patient_ids, rgs_mode="plus", output_file=None)`
- Retrieves time-series RGS interaction data for given patient IDs.
- Filters data based on `rgs_mode`.
- Saves results to a CSV file if `output_file` is specified.

**Example Usage:**
```python
df = fetch_timeseries_data([201, 202], rgs_mode="intensive")
print(df.head())
```

**Example Output (`df.head()`)**:

| SESSION_ID | PATIENT_ID | PROTOCOL_ID | GAME_MODE | SECONDS_FROM_START | PARAMETER_KEY                | PARAMETER_VALUE | PERFORMANCE_KEY           | PERFORMANCE_VALUE |
|------------|-----------|-------------|-----------|--------------------|------------------------------|-----------------|---------------------------|-------------------|
| 16798      | 775       | 224         | STANDARD  | 21633              | standard_dm_targetsNumber   | 0.1             | standard_pe_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 33326              | standard_dm_targetsNumber   | 0.2             | standard_pe_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 47318              | standard_dm_targetsNumber   | 0.3             | standard_pe_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 66509              | standard_dm_targetsNumber   | 0.4             | standard_pe_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 90916              | standard_dm_targetsNumber   | 0.5             | standard_pe_ratioErrors   | 1                 |

</details>

<details>
  <summary>🔹 Fetching Patient IDs</summary>

#### `fetch_patients_by_hospital(hospital_ids)`
- Retrieves a list of patient IDs from specified hospital IDs.
- Accepts a list of hospital IDs and returns matching patient IDs.

**Example Usage:**
```python
patient_ids = fetch_patients_by_hospital([1, 3, 5])
print(patient_ids)
```

---

#### `fetch_patients_by_name(pattern)`
- Fetches patient IDs based on a pattern match in the `PATIENT_USER` field.
- Uses SQL `LIKE` to find patients with names matching the pattern.

**Example Usage:**
```python
matching_patients = fetch_patients_by_name("STU_")
print(matching_patients)
```

---

#### `fetch_patients()`
- Retrieves all patient records from the database.

**Example Usage:**
```python
all_patients = fetch_patients()
print(all_patients.head())
```

</details>

### 📖 CLI

```cmd
fetch-rgs --mode patients --patients 204 775 --rgs-mode plus --dms True
```

Run the script using one of the following methods:

<details>
  <summary>1. Fetch Data for Specific Patients</summary>
</br>
  
You can provide patient IDs directly:
```sh
fetch-rgs --mode patients --patients 204 775 787 788
```

Or, provide a text file where each line contains a patient ID:
```sh
fetch-rgs --mode patients --patients-file patient_ids.txt
```

</details>

<details>
  <summary>2. Fetch Data for Patients in Hospitals</summary>
</br>
 
Provide hospital IDs to fetch all associated patient IDs:
```sh
fetch-rgs --mode hospital --hospital 7 8 9 11 12
```
</details>

<details>
  <summary>3. Set RGS Mode</summary>
</br>
  
You can change the RGS mode (default is `app`) using the `--rgs-mode` flag:
```sh
fetch-rgs --mode patients --patients 204 775 --rgs-mode plus
```

</details>

<details>
  <summary>4. Set DMS Timeseries Data</summary>
</br>

Default: `False` (DMs data not included).

```sh
fetch-rgs --mode patients --patients 204 775 --rgs-mode plus --dms True
```
