## RGS Data Interface

This package provides a Python and command-line interface to fetch Rehabilitation Gaming System (RGS) data for patients.

### Installation

```sh
pip install git+https://github.com/dabadav/rgs-interface@v1.0.0
```

This gives you the Python module and the `rgs-cli` command, talking to the RGS DB API.
Direct database access (only where port 3306 is reachable) needs the `sql` extra:

```sh
pip install "rgs-interface[sql] @ git+https://github.com/dabadav/rgs-interface@v1.0.0"
```

Then store your API url and token once: `rgs-cli credentials set`.

### 📚 Documentation

| Document | What it covers |
| --- | --- |
| [`docs/API_ENDPOINTS.md`](docs/API_ENDPOINTS.md) | Every query: parameters, returned columns, SQL |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Running the API on the database server (install, tokens, service, nginx) |
| [`docs/API_CONTRACT_PLAN.md`](docs/API_CONTRACT_PLAN.md) | Design and the decisions behind it |

### 📖 Python Module Usage

The core functionality for fetching data is provided by two backends with the same interface: `HttpBackend` (goes through the RGS DB API, works from anywhere) and `SqlBackend` (direct MySQL connection, only where port 3306 is reachable). You'll first need to create an instance of one of them.

#### 📦 Main Queries

Once you have an instance (e.g., `db_handler = HttpBackend.from_config()` or `db_handler = SqlBackend.from_config()`), you call `db_handler.fetch(name, **params)` with one of the following query names:

Query Name                   | Description |
|----------------------------|-------------|
| `rgs_data`                 | Retrieves RGS data for a list of patient IDs. |
| `dm_data` / `pe_data`      | Retrieves time-series RGS data (difficulty modulators / performance estimators) for specified patient IDs. |
| `patients`                 | Retrieves patient records; optionally filtered by hospital IDs or by a pattern match in the `PATIENT_USER` field using SQL `LIKE`. |
| `cohort`, `staging`, `prescriptions`, `adherence`, … | Trial-supervision queries: see [`docs/API_ENDPOINTS.md`](docs/API_ENDPOINTS.md). |

<details>
<summary>🔹 Fetching RGS Data</summary>


##### `db_handler.fetch("rgs_data", patient_ids=[...], rgs_mode="plus")`

  - Retrieves RGS interaction data for a list of patient IDs.
  - Allows filtering based on `rgs_mode` (default: `"plus"`).
  - Returns a DataFrame; save it yourself with `df.to_csv(...)` if needed.

**Example Usage:**

```python
from rgs_interface import HttpBackend, SqlBackend

# Create a backend. Credentials are read from the environment, ./.env or ~/.rgs_config.yaml
# (RGS_API_URL / RGS_API_TOKEN for HttpBackend, DB_* for SqlBackend).
db_handler = HttpBackend.from_config()
# db_handler = SqlBackend.from_config()   # direct MySQL, where 3306 is reachable

try:
    df = db_handler.fetch("rgs_data", patient_ids=[101, 102, 103], rgs_mode="app")
    df.to_csv("rgs_data.csv", index=False)
    print(df.head())
finally:
    db_handler.close() # Ensure the connection is closed

# Alternatively, using a context manager:
# with HttpBackend.from_config() as db_handler:
#     df = db_handler.fetch("rgs_data", patient_ids=[101, 102, 103], rgs_mode="app")
#     print(df.head())
```

**Example Output (`df.head()`)**:

| PATIENT\_ID | HOSPITAL\_ID | PARETIC\_SIDE | UPPER\_EXTREMITY\_TO\_TRAIN | HAND\_RAISING\_CAPACITY | COGNITIVE\_FUNCTION\_LEVEL | HAS\_HEMINEGLIGENCE | GENDER  | SKIN\_COLOR | AGE  | VIDEOGAME\_EXP | COMPUTER\_EXP | COMMENTS | PTN\_HEIGHT\_CM | ARM\_SIZE\_CM | PRESCRIPTION\_ID | SESSION\_ID | PROTOCOL\_ID | PRESCRIPTION\_STARTING\_DATE | PRESCRIPTION\_ENDING\_DATE | SESSION\_DATE | STARTING\_HOUR | STARTING\_TIME\_CATEGORY | STATUS  | PROTOCOL\_TYPE | AR\_MODE | WEEKDAY | REAL\_SESSION\_DURATION | PRESCRIBED\_SESSION\_DURATION | SESSION\_DURATION | ADHERENCE | TOTAL\_SUCCESS | TOTAL\_ERRORS | SCORE |
|------------|------------|--------------|---------------------------|------------------------|--------------------------|--------------------|---------|------------|------|---------------|--------------|----------|--------------|------------|----------------|------------|-------------|-------------------------|-------------------------|--------------|--------------|----------------------|---------|--------------|--------|---------|---------------------|-------------------------|----------------|-----------|--------------|-------------|-------|
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78256.0        | 16796.0    | 222.0       | 2024-03-28 08:55:00     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | Hands         | NONE    | FRIDAY  | 492.0               | 300.0                   | 300            | 1.0       | 99            | 8           | 231   |
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78258.0        | 16798.0    | 224.0       | 2024-03-28 08:55:11     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | Hands         | NONE    | FRIDAY  | 338.0               | 300.0                   | 300            | 1.0       | 64            | 17          | 88    |
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78260.0        | 16800.0    | 206.0       | 2024-03-28 08:55:57     | 2100-01-01 00:00:00     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | AR            | TABLE   | FRIDAY  | 280.0               | 240.0                   | 240            | 1.0       | 0             | 0           | 0     |
| 775        | 40          | LEFT         | LEFT                      | LOW                    | MEDIUM                   | 0                  | FEMALE  | FDC3AD     | 88.0 | 0             | 0            |          | 165           | 22         | 78262.0        | 16802.0    | 209.0       | 2024-03-28 08:58:19     | 2024-04-15 15:43:10     | 2024-03-29   | 13.0          | AFTERNOON            | CLOSED  | AR            | TABLE   | FRIDAY  | 391.0               | 300.0                   | 300            | 1.0       | 1             | 2           | 1     |

-----

#### `db_handler.fetch("dm_data", ...)` and `db_handler.fetch("pe_data", ...)`

  - Retrieve time-series RGS interaction data for given patient IDs: difficulty modulators (`dm_data`) and performance estimators (`pe_data`).
  - Filter data based on `rgs_mode`.
  - Merge the two on `SESSION_ID, PATIENT_ID, PROTOCOL_ID, GAME_MODE, SECONDS_FROM_START` to get the combined table below.

**Example Usage:**

```python
from rgs_interface import HttpBackend

db_handler = HttpBackend.from_config()
try:
    dm = db_handler.fetch("dm_data", patient_ids=[201, 202], rgs_mode="plus")
    pe = db_handler.fetch("pe_data", patient_ids=[201, 202], rgs_mode="plus")
    df = dm.merge(pe, on=["SESSION_ID", "PATIENT_ID", "PROTOCOL_ID", "GAME_MODE", "SECONDS_FROM_START"])
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

</details>

<details>
<summary>🔹 Fetching Patient IDs</summary>


#### `db_handler.fetch("patients", hospital_ids=[...])`

  - Retrieves patient records (as a DataFrame) from specified hospital IDs.
  - Accepts a list of hospital IDs.

**Example Usage:**

```python
from rgs_interface import HttpBackend

db_handler = HttpBackend.from_config()
try:
    patient_df = db_handler.fetch("patients", hospital_ids=[1, 3, 5])
    print(patient_df)
    # If you need a list of IDs:
    # patient_ids_list = patient_df["PATIENT_ID"].tolist()
finally:
    db_handler.close()
```

-----

#### `db_handler.fetch("patients", name_like=pattern)`

  - Fetches patient data (e.g., IDs and names) based on a pattern match in the `PATIENT_USER` field.
  - Uses SQL `LIKE` to find patients with names matching the pattern (supply the `%` wildcards yourself).

**Example Usage:**

```python
from rgs_interface import HttpBackend

db_handler = HttpBackend.from_config()
try:
    matching_patients_df = db_handler.fetch("patients", name_like="STU_%")
    print(matching_patients_df)
finally:
    db_handler.close()
```

-----

#### `db_handler.fetch("patients")`

  - Retrieves all patient records from the database (as a DataFrame).

**Example Usage:**

```python
from rgs_interface import HttpBackend

db_handler = HttpBackend.from_config()
try:
    all_patients_df = db_handler.fetch("patients")
    print(all_patients_df.head())
finally:
    db_handler.close()
```

</details>

### 📖 CLI

The CLI is now exposed via:

```bash
rgs-cli <command> [options]
```

#### Available Commands:

| Command             | Description                                                      |
| ------------------- | ---------------------------------------------------------------- |
| `credentials set`   | Set or overwrite the API url/token (and optionally DB credentials) |
| `credentials check` | Check if RGS credentials are already configured                  |
| `fetch`             | Run any query by name and print or save the result               |
| `list-patients`     | List patient IDs by hospital or name pattern                     |

All commands go through the API by default; add `--direct` to use a direct MySQL connection.

#### Example Usage:

```bash
# Set up credentials (force overwrite):
rgs-cli credentials set --force

# Check existing credentials:
rgs-cli credentials check

# Fetch RGS app data for given patients:
rgs-cli fetch rgs_data -p patient_ids=204,775 -p rgs_mode=app -o rgs_data.csv

# Fetch time-series data (parquet keeps the dtypes):
rgs-cli fetch dm_data -p patient_ids=204 -o dm.parquet

# Fetch patients for given hospitals:
rgs-cli fetch patients -p hospital_ids=7,8,9

# Patients whose weekly recommendation is due today in a study:
rgs-cli fetch clinical_trials -p study_id=3 -p due_today=true

# List patient IDs for hospitals or a name pattern:
rgs-cli list-patients --hospital 7 --hospital 8
rgs-cli list-patients --name "AI%"

# Bypass the API (needs DB credentials and port 3306):
rgs-cli fetch rgs_data -p patient_ids=204 --direct
```
