## RGS Data Interface

This package provides a Python and command-line interface to fetch Rehabilitation Gaming System (RGS) data for patients.

### Installation

```sh
pip install rgs_interface-0.2.0.tar.gz
```

### 📖 Python Module Usage

The core functionality for fetching data is provided by the `DatabaseInterface` class, located in the `rgs_interface.data.interface` module. You'll first need to create an instance of this class.

#### 📦 Main Methods of `DatabaseInterface`

Once you have an instance of `DatabaseInterface` (e.g., `db_handler = DatabaseInterface()`), you can call the following methods on it:

Method Name                  | Description |
|----------------------------|-------------|
| `fetch_rgs_data()`         | Retrieves RGS data for a list of patient IDs. |
| `fetch_timeseries_data()`  | Retrieves time-series RGS data for specified patient IDs. |
| `fetch_patients()`         | Retrieves all patient records from the database. |
| `fetch_patients_by_hospital()` | Retrieves patient IDs based on a list of hospital IDs. |
| `fetch_patients_by_name()` | Retrieves patient IDs based on a pattern match in the `PATIENT_USER` field using SQL `LIKE`. |

\<details\>
\<summary\>🔹 Fetching RGS Data\</summary\>

##### `db_handler.fetch_rgs_data(patient_ids, rgs_mode="plus", output_file=None)`

  - Retrieves RGS interaction data for a list of patient IDs.
  - Allows filtering based on `rgs_mode` (default: `"plus"`).
  - Saves the results as a CSV file if `output_file` is specified.

**Example Usage:**

```python
from rgs_interface.data.interface import DatabaseInterface # Adjust import path if needed

# Create an instance of the DatabaseInterface
# This will handle database connection setup internally.
db_handler = DatabaseInterface()

try:
    df = db_handler.fetch_rgs_data([101, 102, 103], rgs_mode="app", output_file="rgs_data.csv")
    if df is not None:
        print(df.head())
finally:
    db_handler.close() # Ensure the database connection is closed

# Alternatively, using a context manager (if your class supports it):
# with DatabaseInterface() as db_handler:
#     df = db_handler.fetch_rgs_data([101, 102, 103], rgs_mode="app", output_file="rgs_data.csv")
#     if df is not None:
#         print(df.head())
```

**Example Output (`df.head()`)**:

| PATIENT\_ID | HOSPITAL\_ID | PARETIC\_SIDE | UPPER\_EXTREMITY\_TO\_TRAIN | HAND\_RAISING\_CAPACITY | COGNITIVE\_FUNCTION\_LEVEL | HAS\_HEMINEGLIGENCE | GENDER  | SKIN\_COLOR | AGE  | VIDEOGAME\_EXP | COMPUTER\_EXP | COMMENTS | PTN\_HEIGHT\_CM | ARM\_SIZE\_CM | PRESCRIPTION\_ID | SESSION\_ID | PROTOCOL\_ID | PRESCRIPTION\_STARTING\_DATE | PRESCRIPTION\_ENDING\_DATE | SESSION\_DATE | STARTING\_HOUR | STARTING\_TIME\_CATEGORY | STATUS  | PROTOCOL\_TYPE | AR\_MODE | WEEKDAY | REAL\_SESSION\_DURATION | PRESCRIBED\_SESSION\_DURATION | SESSION\_DURATION | ADHERENCE | TOTAL\_SUCCESS | TOTAL\_ERRORS | SCORE |
|------------|------------|--------------|---------------------------|------------------------|--------------------------|--------------------|---------|------------|------|---------------|--------------|----------|--------------|------------|----------------|------------|-------------|-------------------------|-------------------------|--------------|--------------|----------------------|---------|--------------|--------|---------|---------------------|-------------------------|----------------|-----------|--------------|-------------|-------|
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78256.0        | 16796.0    | 222.0       | 2024-03-28 08:55:00     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | Hands         | NONE    | FRIDAY  | 492.0               | 300.0                   | 300            | 1.0       | 99            | 8           | 231   |
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78258.0        | 16798.0    | 224.0       | 2024-03-28 08:55:11     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | Hands         | NONE    | FRIDAY  | 338.0               | 300.0                   | 300            | 1.0       | 64            | 17          | 88    |
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78260.0        | 16800.0    | 206.0       | 2024-03-28 08:55:57     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | AR            | TABLE   | FRIDAY  | 280.0               | 240.0                   | 240            | 1.0       | 0             | 0           | 0     |
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78262.0        | 16802.0    | 209.0       | 2024-03-28 08:58:19     | 2024-04-15 15:43:10     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | AR            | TABLE   | FRIDAY  | 391.0               | 300.0                   | 300            | 1.0       | 1             | 2           | 1     |

-----

#### `db_handler.fetch_timeseries_data(patient_ids, rgs_mode="plus", output_file=None)`

  - Retrieves time-series RGS interaction data for given patient IDs.
  - Filters data based on `rgs_mode`.
  - Saves results to a CSV file if `output_file` is specified.

**Example Usage:**

```python
from rgs_interface.data.interface import DatabaseInterface # Adjust import path if needed

db_handler = DatabaseInterface()
try:
    df = db_handler.fetch_timeseries_data([201, 202], rgs_mode="intensive")
    if df is not None:
        print(df.head())
finally:
    db_handler.close()
```

**Example Output (`df.head()`)**:

| SESSION\_ID | PATIENT\_ID | PROTOCOL\_ID | GAME\_MODE | SECONDS\_FROM\_START | PARAMETER\_KEY                | PARAMETER\_VALUE | PERFORMANCE\_KEY           | PERFORMANCE\_VALUE |
|------------|-----------|-------------|-----------|--------------------|------------------------------|-----------------|---------------------------|-------------------|
| 16798      | 775       | 224         | STANDARD  | 21633              | standard\_dm\_targetsNumber    | 0.1             | standard\_pe\_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 33326              | standard\_dm\_targetsNumber    | 0.2             | standard\_pe\_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 47318              | standard\_dm\_targetsNumber    | 0.3             | standard\_pe\_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 66509              | standard\_dm\_targetsNumber    | 0.4             | standard\_pe\_ratioErrors   | 1                 |
| 16798      | 775       | 224         | STANDARD  | 90916              | standard\_dm\_targetsNumber    | 0.5             | standard\_pe\_ratioErrors   | 1                 |

\</details\>

\<details\>
\<summary\>🔹 Fetching Patient IDs\</summary\>

#### `db_handler.fetch_patients_by_hospital(hospital_ids)`

  - Retrieves a list of patient IDs (typically as a DataFrame column) from specified hospital IDs.
  - Accepts a list of hospital IDs.

**Example Usage:**

```python
from rgs_interface.data.interface import DatabaseInterface # Adjust import path if needed

db_handler = DatabaseInterface()
try:
    patient_df = db_handler.fetch_patients_by_hospital([1, 3, 5])
    if patient_df is not None:
        print(patient_df) # This will likely be a DataFrame
        # If you need a list of IDs:
        # patient_ids_list = patient_df['PATIENT_ID'].tolist() if 'PATIENT_ID' in patient_df else []
        # print(patient_ids_list)
finally:
    db_handler.close()
```

-----

#### `db_handler.fetch_patients_by_name(pattern)`

  - Fetches patient data (e.g., IDs and names) based on a pattern match in the `PATIENT_USER` field.
  - Uses SQL `LIKE` to find patients with names matching the pattern.

**Example Usage:**

```python
from rgs_interface.data.interface import DatabaseInterface # Adjust import path if needed

db_handler = DatabaseInterface()
try:
    matching_patients_df = db_handler.fetch_patients_by_name("STU_")
    if matching_patients_df is not None:
        print(matching_patients_df) # This will likely be a DataFrame
finally:
    db_handler.close()
```

-----

#### `db_handler.fetch_patients()`

  - Retrieves all patient records from the database (typically as a DataFrame).

**Example Usage:**

```python
from rgs_interface.data.interface import DatabaseInterface # Adjust import path if needed

db_handler = DatabaseInterface()
try:
    all_patients_df = db_handler.fetch_patients()
    if all_patients_df is not None:
        print(all_patients_df.head())
finally:
    db_handler.close()
```

\</details\>

Here’s a clean, minimal update that reflects your latest CLI changes (using `rgs-cli` and Typer-based subcommands), without cluttering the existing document structure. I’ll leave the Python module section mostly intact and **only replace the outdated CLI section** with the new `rgs-cli` interface.

---

### 📖 CLI

The CLI is now exposed via:

```bash
rgs-cli <command> [options]
```

#### Available Commands:

| Command             | Description                                               |
| ------------------- | --------------------------------------------------------- |
| `credentials set`   | Set or overwrite RGS database credentials                 |
| `credentials check` | Check if RGS credentials are already configured           |
| `fetch`             | Fetch RGS data for specific patients, hospitals, or study |
| `list-patients`     | List patient IDs by hospital or study                     |

#### Example Usage:

```bash
# Set up credentials (force overwrite):
rgs-cli credentials set --force

# Check existing credentials:
rgs-cli credentials check

# Fetch RGS app data for given patients:
rgs-cli fetch --patients 204 775 --rgs-mode app --output-file rgs_data.csv

# Fetch RGS data using a text file with patient IDs (one ID per line):
rgs-cli fetch --patients-file patient_ids.txt --rgs-mode plus

# Fetch patients for a given hospital:
rgs-cli fetch --hospital 7 8 9

# Fetch patients for a given study:
rgs-cli fetch --study STUDY_ID_001

# List patient IDs for a study:
rgs-cli list-patients --study STUDY_ID_001
```

-----

**Key Documentation Changes:**

  * **Preamble for Python Usage**: Added a sentence stating that functionality is through the `DatabaseInterface` class.
  * **Method Table**: Clarified that these are methods of an instance of `DatabaseInterface`.
  * **Method Signatures in Headings**: Updated method headings to reflect they are called on an instance (e.g., `db_handler.fetch_rgs_data(...)`).
  * **Example Usage Blocks**:
      * Added `from rgs_interface.data.interface import DatabaseInterface` (emphasizing that the import path might need adjustment).
      * Added instantiation: `db_handler = DatabaseInterface()`.
      * Changed function calls to method calls: `df = db_handler.fetch_rgs_data(...)`.
      * Added a `try...finally` block with `db_handler.close()` to demonstrate proper resource management. I also added a commented-out example of using a `with` statement if your `DatabaseInterface` class is implemented as a context manager (which it was in our previous discussions).
      * For methods like `fetch_patients_by_hospital` that return DataFrames, I added a comment on how one might extract a list of IDs, as the original example implied a direct list return.
  * **CLI Section**: This section remains unchanged as the command-line tool's usage from a user's perspective would not change, even if its internal implementation now uses the `DatabaseInterface` class.
