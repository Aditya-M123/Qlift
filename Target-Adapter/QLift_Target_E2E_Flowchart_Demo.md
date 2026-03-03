# QLift Target Module - End-to-End Flowchart & Demo Guide

## Project Overview

**QLift** is a database migration verification platform that translates and validates SQL migrations from source databases (e.g., Oracle) to target databases (e.g., Google BigQuery). The **Target module** is responsible for defining how QLift talks to any target database, testing adapter compliance, and providing a concrete BigQuery implementation.

---

## User Stories at a Glance

| Story ID | Title | Purpose |
|----------|-------|---------|
| **TA-01a** | Target Adapter Contract & Schemas | Define the abstract rulebook every adapter must follow |
| **TA-01b** | Compliance Harness | Automated test runner to verify any adapter obeys the rulebook |
| **TA-02** | BigQuery Adapter | Concrete implementation for Google BigQuery |

---

## Architecture Diagram

```
+------------------------------------------------------------------+
|                        QLift Verify Service                      |
|                  (only knows about TargetAdapter)                 |
+------------------------------------------------------------------+
                              |
                    imports abstract contract
                              |
                              v
+------------------------------------------------------------------+
|                  TA-01a: Abstract Contract Layer                  |
|                                                                  |
|   +---------------------+    +-----------------------------+     |
|   |   TargetAdapter      |    |   Data Schemas              |     |
|   |   (Abstract Class)   |    |                             |     |
|   |                      |    |   ColumnProfile             |     |
|   |   - connect()        |    |     .name                   |     |
|   |   - get_dialect_name()|   |     .type                   |     |
|   |   - get_grammar()    |    |     .nullable               |     |
|   |   - get_type_mapping()|   |     .precision_warning      |     |
|   |   - create_sandbox() |    |                             |     |
|   |   - destroy_sandbox()|    |   TableProfile              |     |
|   |   - deploy_ddl()     |    |     .sandbox_id             |     |
|   |   - load_test_data() |    |     .table_name             |     |
|   |   - execute_query()  |    |     .row_count              |     |
|   |   - get_table_profile()|  |     .columns: [ColumnProfile]|    |
|   |   - generate_ddl()   |    |                             |     |
|   +---------------------+    +-----------------------------+     |
+------------------------------------------------------------------+
          |                                       |
    implements                              used by
          |                                       |
          v                                       v
+-------------------------+     +----------------------------------+
| TA-02: BigQueryAdapter  |     | TA-01b: Compliance Harness       |
|                         |     |                                  |
| - Workload Identity Auth|     | - Loads any adapter dynamically  |
| - Oracle->BQ Type Map   |     | - Runs all 9 contract methods    |
| - DDL Generator         |     | - Checks return types            |
| - Sandbox Lifecycle     |     | - Guarantees destroy_sandbox()   |
+-------------------------+     | - Reports PASS / FAIL / SKIP     |
                                +----------------------------------+
```

---

## STORY TA-01a: Target Adapter Contract & Schemas

### What It Is
The abstract "rulebook" that defines the interface every target database adapter must implement. No database-specific code lives here. No BigQuery SDK imports allowed.

### Files
- `qlift/target/ta01a/adapter.py` - Abstract base class `TargetAdapter`
- `qlift/target/ta01a/schemas.py` - Data classes `ColumnProfile` and `TableProfile`

### TA-01a Flowchart

```
  START: Define Contract
         |
         v
+-----------------------------+
| Define ColumnProfile        |
| (dataclass)                 |
|                             |
| Fields:                     |
|   - name: str               |
|   - type: str               |
|   - nullable: bool          |
|   - precision_warning: str? |
+-----------------------------+
         |
         v
+-----------------------------+
| Define TableProfile         |
| (dataclass)                 |
|                             |
| Fields:                     |
|   - sandbox_id: str         |
|   - table_name: str         |
|   - row_count: int          |
|   - columns: [ColumnProfile]|
+-----------------------------+
         |
         v
+-----------------------------+
| Define TargetAdapter        |
| (Abstract Base Class)       |
|                             |
| 10 Abstract Methods:        |
+-----------------------------+
         |
         +---> connect(config)              --> Authenticate with target DB
         +---> get_dialect_name()           --> Return "bigquery" / "alloydb" / etc.
         +---> get_grammar()                --> Return SQL grammar for validator
         +---> get_type_mapping(dialect)    --> Return {source_type: target_type} dict
         +---> create_sandbox(name)         --> Create temp test environment --> return ID
         +---> destroy_sandbox(sandbox_id)  --> Delete sandbox (ALWAYS called)
         +---> deploy_ddl(sandbox_id, ddl)  --> Execute CREATE TABLE / VIEW
         +---> load_test_data(sandbox_id, table, data) --> Insert test rows --> return count
         +---> execute_query(sandbox_id, query) --> Run SQL --> return rows as List[Dict]
         +---> get_table_profile(sandbox_id, table) --> Collect stats --> return TableProfile
         +---> generate_ddl(schema_def, recommendations) --> Build CREATE TABLE SQL
         |
         v
+-----------------------------+
| Constraint: ZERO database-  |
| specific imports allowed    |
| No google.cloud, no SDK    |
+-----------------------------+
         |
         v
    END: Contract Ready
```

### Demo Walkthrough for TA-01a

**Step 1: Show that TargetAdapter cannot be instantiated directly**
```python
from qlift.target.ta01a.adapter import TargetAdapter

# This MUST raise TypeError - it's abstract
try:
    adapter = TargetAdapter()
except TypeError as e:
    print(f"Correct! Cannot instantiate abstract class: {e}")
```

**Step 2: Show schema objects work correctly**
```python
from qlift.target.ta01a.schemas import ColumnProfile, TableProfile

col = ColumnProfile(
    name="order_date",
    type="DATETIME",
    nullable=False,
    precision_warning=None
)
print(f"Column: {col.name} -> {col.type}, nullable={col.nullable}")

profile = TableProfile(
    sandbox_id="qlift_sandbox_test123",
    table_name="orders",
    row_count=500,
    columns=[col]
)
print(f"Table: {profile.table_name}, rows={profile.row_count}")
```

**Step 3: Show no BigQuery imports exist in contract files**
```python
# The contract files must have ZERO google.cloud imports
# This keeps the contract database-agnostic
import inspect, qlift.target.ta01a.adapter as m
source = inspect.getsource(m)
assert "google.cloud" not in source  # PASS
```

### Tests (6 tests in `tests/target/ta01a/test_ta01a.py`)
| # | Test | What It Proves |
|---|------|----------------|
| 1 | `test_target_adapter_raises_type_error` | Abstract class cannot be used directly |
| 2 | `test_table_profile_columns_returns_list_of_column_profiles` | TableProfile.columns is List[ColumnProfile] |
| 3 | `test_column_profile_stores_values_correctly` | All fields stored & returned correctly |
| 4 | `test_column_profile_precision_warning_can_be_none` | precision_warning accepts None |
| 5 | `test_no_bigquery_imports_in_contract_files` | Zero BigQuery SDK imports in contract layer |
| 6 | `test_table_profile_stores_row_count` | row_count, table_name, sandbox_id all correct |

---

## STORY TA-01b: Compliance Harness

### What It Is
An automated test runner that takes ANY adapter implementation, runs all 10 contract methods in sequence, checks return types, and guarantees `destroy_sandbox()` is always called -- even if the adapter crashes mid-run. Prevents orphaned sandboxes in GCP.

### Files
- `qlift/target/ta01b/harness.py` - The harness runner + CLI entry point

### TA-01b Full Flowchart

```
  START: run_harness(adapter, config)
         |
         v
+------------------------------+
| Print Header                 |
| "QLift Target Adapter        |
|  Compliance Harness"         |
| Adapter: <class name>        |
+------------------------------+
         |
         v
+==============================================+
| TRY BLOCK (protected by finally)             |
|                                              |
|  Step 1: connect(config)                     |
|          |                                   |
|          +---> Success? --> [PASS] connect    |
|          +---> Exception? --> [FAIL] connect  |
|          v                                   |
|  Step 2: get_dialect_name()                  |
|          |                                   |
|          +---> Returns str? --> [PASS]        |
|          +---> Wrong type?  --> [FAIL]        |
|          +---> Exception?   --> [FAIL]        |
|          v                                   |
|  Step 3: get_type_mapping("oracle")          |
|          |                                   |
|          +---> Returns dict? --> [PASS]       |
|          +---> Wrong type?   --> [FAIL]       |
|          +---> Exception?    --> [FAIL]       |
|          v                                   |
|  Step 4: create_sandbox("harness_test")      |
|          |                                   |
|          +---> Returns str?  --> [PASS]       |
|          |     (saves sandbox_id)            |
|          +---> Wrong type?   --> [FAIL]       |
|          +---> Exception?    --> [FAIL]       |
|          v                                   |
|  Step 5: deploy_ddl(sandbox_id, TEST_DDL)    |
|          |                                   |
|          |   TEST_DDL:                        |
|          |   CREATE TABLE harness_test_table  |
|          |   (id INTEGER, name STRING,        |
|          |    amount NUMERIC)                 |
|          |                                   |
|          +---> Success? --> [PASS]            |
|          +---> Exception? --> [FAIL]          |
|          v                                   |
|  Step 6: load_test_data(sandbox_id,          |
|          "harness_test_table", TEST_DATA)     |
|          |                                   |
|          |   TEST_DATA:                       |
|          |   [{id:1, name:"Alice", amt:100.50}|
|          |    {id:2, name:"Bob",   amt:200.75}|
|          |    {id:3, name:"Carol", amt:300.00}]|
|          |                                   |
|          +---> Returns int? --> [PASS]        |
|          +---> Wrong type?  --> [FAIL]        |
|          +---> Exception?   --> [FAIL]        |
|          v                                   |
|  Step 7: execute_query(sandbox_id,           |
|          "SELECT * FROM harness_test_table")  |
|          |                                   |
|          +---> Returns list? --> [PASS]       |
|          +---> Wrong type?   --> [FAIL]       |
|          +---> Exception?    --> [FAIL]       |
|          v                                   |
|  Step 8: get_table_profile(sandbox_id,       |
|          "harness_test_table")                |
|          |                                   |
|          +---> Returns TableProfile? -> [PASS]|
|          +---> Wrong type?           -> [FAIL]|
|          +---> Exception?            -> [FAIL]|
|                                              |
+==============================================+
         |
         | FINALLY (ALWAYS RUNS)
         v
+------------------------------+
| Step 9: destroy_sandbox()    |
|                              |
| Was sandbox_id created?      |
|   |                          |
|   +-- YES --> destroy_sandbox|
|   |           (sandbox_id)   |
|   |           |              |
|   |           +-> [PASS]     |
|   |           +-> [FAIL]     |
|   |                          |
|   +-- NO  --> [SKIP]         |
|         "sandbox was never   |
|          created"            |
+------------------------------+
         |
         v
+------------------------------+
| Print Results Summary        |
|                              |
| Each method: [PASS]/[FAIL]   |
| Total: X/9 PASSED            |
|                              |
| All pass? --> "All checks    |
|                passed"       |
| Some fail? -> "Some checks   |
|                failed"       |
+------------------------------+
         |
         v
    END: Return results dict
```

### Key Safety Guarantee

```
+----------------------------------------------------------------+
|                   CRASH SAFETY GUARANTEE                        |
|                                                                 |
|   Even if ANY step between 1-8 throws an exception,            |
|   the FINALLY block ensures destroy_sandbox() is ALWAYS called. |
|                                                                 |
|   WHY? Orphaned sandbox datasets in BigQuery cost real money    |
|   and violate GCP resource governance.                          |
|                                                                 |
|   SCENARIO 1: deploy_ddl crashes                                |
|     Step 5 throws RuntimeError                                  |
|     --> Steps 6-8 are skipped                                   |
|     --> Step 9 (destroy_sandbox) STILL RUNS                     |
|     --> Sandbox is cleaned up                                   |
|                                                                 |
|   SCENARIO 2: create_sandbox crashes                            |
|     Step 4 throws RuntimeError                                  |
|     --> sandbox_id is None                                      |
|     --> Step 9 sees sandbox_id=None --> [SKIP]                  |
|     --> No crash, no orphaned resources                         |
|                                                                 |
|   SCENARIO 3: connect fails                                     |
|     Step 1 throws ConnectionError                               |
|     --> Steps 2-8 still attempted (may fail)                    |
|     --> Step 9 sees sandbox_id=None --> [SKIP]                  |
+----------------------------------------------------------------+
```

### CLI Usage Flow

```
  User runs from terminal:
         |
         v
  python -m qlift.target.ta01b.harness --adapter bigquery --project my-gcp-project
         |
         v
+-----------------------------+
| Parse CLI Arguments         |
|   --adapter: "bigquery"     |
|   --project: "my-gcp-project"|
+-----------------------------+
         |
         v
+-----------------------------+
| Dynamic Adapter Loading     |
|                             |
| adapter_map = {             |
|   "bigquery": "qlift.target.|
|    ta02.bigquery.adapter.   |
|    BigQueryAdapter"         |
| }                           |
|                             |
| importlib.import_module()   |
| getattr(module, class_name) |
+-----------------------------+
         |
         v
+-----------------------------+
| Create adapter instance     |
| config = {                  |
|   "project_id": args.project|
| }                           |
+-----------------------------+
         |
         v
  run_harness(adapter, config)
         |
         v
  (see harness flowchart above)
```

### Demo Walkthrough for TA-01b

**Step 1: Good adapter - all checks pass**
```python
from tests.target.ta01b.test_ta01b import GoodMockAdapter
from qlift.target.ta01b.harness import run_harness

adapter = GoodMockAdapter()
results = run_harness(adapter, config={})
# Output: 9/9 PASSED, All checks passed
```

**Step 2: Bad adapter - wrong return type detected**
```python
from tests.target.ta01b.test_ta01b import BadMockAdapter

adapter = BadMockAdapter()
results = run_harness(adapter, config={})
# Output: execute_query shows [FAIL] - expected list, got str
```

**Step 3: Crashing adapter - sandbox still destroyed**
```python
from tests.target.ta01b.test_ta01b import CrashingMockAdapter

adapter = CrashingMockAdapter()
results = run_harness(adapter, config={})
# deploy_ddl shows [FAIL], but destroy_sandbox shows [PASS]
# adapter.destroy_called == True  <-- safety guarantee proven
```

### Tests (6 tests in `tests/target/ta01b/test_ta01b.py`)
| # | Test | What It Proves |
|---|------|----------------|
| 1 | `test_good_adapter_all_pass` | Correct adapter gets all PASS |
| 2 | `test_bad_adapter_execute_query_reports_fail` | Wrong return type detected as FAIL |
| 3 | `test_destroy_sandbox_called_even_after_crash` | Sandbox cleanup guaranteed on crash |
| 4 | `test_check_type_returns_pass_for_correct_type` | Type checker helper works for correct types |
| 5 | `test_check_type_returns_fail_for_wrong_type` | Type checker helper catches wrong types |
| 6 | `test_harness_skips_destroy_when_sandbox_never_created` | No crash when sandbox was never created |
| 7 | `test_create_sandbox_raises_destroy_still_called` | Cleanup is graceful even if create_sandbox fails |

---

## STORY TA-02: BigQuery Adapter (Concrete Implementation)

### What It Is
The concrete implementation of the TA-01a contract for Google BigQuery. Includes Oracle-to-BigQuery type mapping, DDL generation with partitioning/clustering, and full sandbox lifecycle management.

### Files
- `qlift/target/ta02/bigquery/adapter.py` - `BigQueryAdapter` class
- `qlift/target/ta02/bigquery/type_mapping.py` - Oracle-to-BigQuery type conversion table
- `qlift/target/ta02/bigquery/ddl_generator.py` - CREATE TABLE statement builder

### TA-02 Component Architecture

```
+------------------------------------------------------------------+
|                     BigQueryAdapter                               |
|                (implements TargetAdapter)                         |
|                                                                  |
|  +---------------------------+  +-----------------------------+  |
|  | Workload Identity Auth    |  | Type Mapping Module         |  |
|  |                           |  |                             |  |
|  | - No JSON key files       |  | ORACLE_TO_BIGQUERY dict     |  |
|  | - GCP handles auth        |  |   VARCHAR2  --> STRING      |  |
|  | - Local: gcloud auth      |  |   NUMBER    --> NUMERIC     |  |
|  | - GKE: Workload Identity  |  |   DATE      --> DATETIME    |  |
|  +---------------------------+  |   TIMESTAMP --> TIMESTAMP   |  |
|                                 |   BLOB      --> BYTES       |  |
|  +---------------------------+  |   CLOB      --> STRING      |  |
|  | DDL Generator             |  |   XMLTYPE   --> JSON (lossy)|  |
|  |                           |  |                             |  |
|  | - CREATE TABLE statement  |  | LOSSY_MAPPINGS set          |  |
|  | - PARTITION BY clause     |  |   {XMLTYPE, FLOAT,          |  |
|  | - CLUSTER BY clause       |  |    BINARY_FLOAT,            |  |
|  | - NOT NULL constraints    |  |    BINARY_DOUBLE}           |  |
|  | - Lossy conversion warns  |  +-----------------------------+  |
|  +---------------------------+                                   |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  | Sandbox Lifecycle                                          |  |
|  |                                                            |  |
|  |  create_sandbox() --> BQ Dataset (qlift_sandbox_<name>_xx) |  |
|  |  deploy_ddl()     --> Run CREATE TABLE in sandbox          |  |
|  |  load_test_data() --> insert_rows_json() into sandbox      |  |
|  |  execute_query()  --> Run SELECT in sandbox --> List[Dict] |  |
|  |  get_table_profile() --> Row count + column metadata       |  |
|  |  destroy_sandbox() --> Delete dataset + all contents       |  |
|  +-----------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### TA-02 Type Mapping Flowchart (Critical Business Rules)

```
  Oracle Source Column
         |
         v
+-----------------------------+
| Look up source type in      |
| ORACLE_TO_BIGQUERY dict     |
+-----------------------------+
         |
    +----+----+----+----+----+----+----+
    |    |    |    |    |    |    |    |
    v    v    v    v    v    v    v    v

 VARCHAR2  NUMBER  DATE   TIMESTAMP  BLOB  CLOB  XMLTYPE  INTEGER
    |       |       |        |        |      |      |        |
    v       v       v        v        v      v      v        v
 STRING  NUMERIC DATETIME TIMESTAMP BYTES STRING   JSON    INT64


    CRITICAL RULE 1:               CRITICAL RULE 2:
    DATE --> DATETIME              NUMBER --> NUMERIC
    (NOT DATE)                     (NOT FLOAT64)

    WHY?                           WHY?
    Oracle DATE stores             Oracle NUMBER has exact
    date AND time:                 decimal precision:
    2024-01-15 14:32:00            99.99 stays 99.99

    BigQuery DATE stores           BigQuery FLOAT64 loses
    only date:                     precision:
    2024-01-15                     99.99 becomes 99.98999...

    MAPPING TO DATE =              MAPPING TO FLOAT64 =
    SILENT TIME LOSS               SILENT PRECISION LOSS

         |
         v
+-----------------------------+
| Check LOSSY_MAPPINGS set    |
|                             |
| Is source type lossy?       |
|   |                         |
|   +-- YES: XMLTYPE, FLOAT,  |
|   |   BINARY_FLOAT,         |
|   |   BINARY_DOUBLE         |
|   |   --> precision_warning  |
|   |       added to column   |
|   |                         |
|   +-- NO: Safe conversion   |
|       --> no warning         |
+-----------------------------+
         |
         v
+-----------------------------+
| Type not found in mapping?  |
|   --> Falls back to STRING  |
|                             |
| Unsupported dialect?        |
|   --> Raises ValueError     |
+-----------------------------+
```

### TA-02 DDL Generation Flowchart

```
  INPUT:
    schema_def = {
      project: "my-gcp-project",
      dataset: "sales",
      table_name: "orders",
      columns: [{name, source_type, nullable}, ...]
    }
    recommendations = {
      partition_column: "order_date",
      cluster_columns: ["customer_id", "status"]
    }
         |
         v
+-----------------------------+
| Step 1: Build Table Ref     |
|                             |
| Has project + dataset?      |
|   --> `project.dataset.table`|
| Has dataset only?           |
|   --> `dataset.table`       |
| Neither?                    |
|   --> `table`               |
+-----------------------------+
         |
         v
+-----------------------------+
| Step 2: Build Column Lines  |
| For each column:            |
|   |                         |
|   +-> Convert Oracle type   |
|   |   to BigQuery type      |
|   |   (via get_bigquery_type)|
|   |                         |
|   +-> nullable=False?       |
|   |   Add "NOT NULL"        |
|   |                         |
|   +-> Is source type lossy? |
|       Add SQL comment:      |
|       -- WARNING: lossy     |
|          conversion from X  |
+-----------------------------+
         |
         v
+-----------------------------+
| Step 3: PARTITION BY        |
|                             |
| partition_column set?       |
|   |                         |
|   +-- YES:                  |
|   |   PARTITION BY DATE(col)|
|   |                         |
|   +-- NO:                   |
|       (no partition clause) |
+-----------------------------+
         |
         v
+-----------------------------+
| Step 4: CLUSTER BY          |
|                             |
| cluster_columns set?        |
|   |                         |
|   +-- YES:                  |
|   |   CLUSTER BY col1, col2 |
|   |   (max 4 columns)       |
|   |                         |
|   +-- NO:                   |
|       (no cluster clause)   |
+-----------------------------+
         |
         v
+-----------------------------+
| Step 5: Assemble DDL        |
+-----------------------------+
         |
         v
  OUTPUT:
    CREATE TABLE `my-gcp-project.sales.orders`
    (
      order_id      NUMERIC  NOT NULL,
      order_date    DATETIME NOT NULL,
      amount        NUMERIC
    )
    PARTITION BY DATE(order_date)
    CLUSTER BY customer_id, status;
```

### TA-02 Sandbox Lifecycle Flowchart

```
  START: BigQueryAdapter
         |
         v
+-----------------------------+
| connect(config)             |
|                             |
| config.project_id missing?  |
|   --> Raise ValueError      |
|                             |
| Auth via Workload Identity  |
| (no JSON key files)         |
|                             |
| Local dev:                  |
|   gcloud auth               |
|   application-default login |
|                             |
| GKE production:             |
|   Workload Identity bindings|
|                             |
| Creates bigquery.Client     |
+-----------------------------+
         |
         v
+-----------------------------+
| create_sandbox(name)        |
|                             |
| Generate unique ID:         |
|   qlift_sandbox_<name>_     |
|   <8-char-uuid>             |
|                             |
| Create BigQuery Dataset     |
|   Location: "US"            |
|   exists_ok: True           |
|                             |
| Return: sandbox_id          |
+-----------------------------+
         |
         v
+-----------------------------+
| deploy_ddl(sandbox_id, ddl) |
|                             |
| Execute DDL via             |
|   client.query(ddl)         |
|   job.result() -- wait      |
|                             |
| Creates tables/views inside |
| the sandbox dataset         |
+-----------------------------+
         |
         v
+-----------------------------+
| load_test_data(sandbox_id,  |
|   table, data)              |
|                             |
| Table ref:                  |
|   project.sandbox.table     |
|                             |
| client.insert_rows_json()   |
|                             |
| Errors? --> Raise Runtime   |
| Success --> Return len(data)|
+-----------------------------+
         |
         v
+-----------------------------+
| execute_query(sandbox_id,   |
|   query)                    |
|                             |
| client.query(query)         |
| job.result()                |
|                             |
| Return: [dict(row) for row] |
+-----------------------------+
         |
         v
+-----------------------------+
| get_table_profile(          |
|   sandbox_id, table)        |
|                             |
| 1. Get table metadata       |
|    client.get_table()       |
|                             |
| 2. Count rows               |
|    SELECT COUNT(*) ...      |
|                             |
| 3. Build ColumnProfile      |
|    for each schema field:   |
|    - name, type, nullable   |
|    - precision_warning      |
|      (if lossy type)        |
|                             |
| Return: TableProfile(       |
|   sandbox_id, table_name,   |
|   row_count, [columns])     |
+-----------------------------+
         |
         v
+-----------------------------+
| destroy_sandbox(sandbox_id) |
|                             |
| client.delete_dataset(      |
|   project.sandbox,          |
|   delete_contents=True,     |
|   not_found_ok=True)        |
|                             |
| ALWAYS called - guaranteed  |
| by harness finally block    |
+-----------------------------+
         |
         v
    END: Sandbox cleaned up
```

### Demo Walkthrough for TA-02

**Step 1: Type Mapping - Show critical rules**
```python
from qlift.target.ta02.bigquery.type_mapping import get_type_mapping, is_lossy

mapping = get_type_mapping("oracle")

# Critical Rule 1: DATE -> DATETIME (not DATE)
print(f"Oracle DATE    -> BigQuery {mapping['DATE']}")      # DATETIME
# Critical Rule 2: NUMBER -> NUMERIC (not FLOAT64)
print(f"Oracle NUMBER  -> BigQuery {mapping['NUMBER']}")    # NUMERIC

# Show lossy detection
print(f"XMLTYPE is lossy: {is_lossy('XMLTYPE')}")  # True
print(f"VARCHAR2 is lossy: {is_lossy('VARCHAR2')}") # False

# Unsupported dialect raises error
try:
    get_type_mapping("unsupported_db")
except ValueError as e:
    print(f"Caught: {e}")
```

**Step 2: DDL Generation - Show complete output**
```python
from qlift.target.ta02.bigquery.ddl_generator import generate_ddl

schema_def = {
    "project":    "my-gcp-project",
    "dataset":    "sales",
    "table_name": "orders",
    "columns": [
        {"name": "order_id",   "source_type": "NUMBER",   "nullable": False},
        {"name": "order_date", "source_type": "DATE",     "nullable": False},
        {"name": "amount",     "source_type": "NUMBER",   "nullable": True},
        {"name": "xml_data",   "source_type": "XMLTYPE",  "nullable": True},
    ]
}
recommendations = {
    "partition_column": "order_date",
    "cluster_columns":  ["order_id"]
}

ddl = generate_ddl(schema_def, recommendations)
print(ddl)

# Output:
# CREATE TABLE `my-gcp-project.sales.orders`
# (
#   order_id       NUMERIC  NOT NULL,
#   order_date     DATETIME  NOT NULL,
#   amount         NUMERIC,
#   xml_data       JSON  -- WARNING: lossy conversion from XMLTYPE
# )
# PARTITION BY DATE(order_date)
# CLUSTER BY order_id;
```

**Step 3: Adapter - Show contract compliance**
```python
from qlift.target.ta02.bigquery.adapter import BigQueryAdapter

adapter = BigQueryAdapter()

# Dialect name
print(f"Dialect: {adapter.get_dialect_name()}")  # "bigquery"

# Type mapping works without connection
mapping = adapter.get_type_mapping("oracle")
print(f"Type mapping has {len(mapping)} entries")

# DDL generation works without connection
ddl = adapter.generate_ddl(schema_def, recommendations)
print(f"DDL generated: {len(ddl)} chars")

# But sandbox operations require connection first
try:
    adapter.create_sandbox("test")
except RuntimeError as e:
    print(f"Correct! Must connect first: {e}")
```

### Tests (17 tests in `tests/target/ta02/test_ta02.py`)
| # | Test | What It Proves |
|---|------|----------------|
| 1 | `test_oracle_date_maps_to_datetime` | DATE -> DATETIME (not DATE) |
| 2 | `test_oracle_number_maps_to_numeric` | NUMBER -> NUMERIC (not FLOAT64) |
| 3 | `test_oracle_varchar2_maps_to_string` | VARCHAR2 -> STRING |
| 4 | `test_oracle_clob_maps_to_string` | CLOB -> STRING |
| 5 | `test_oracle_blob_maps_to_bytes` | BLOB -> BYTES |
| 6 | `test_oracle_timestamp_maps_to_timestamp` | TIMESTAMP -> TIMESTAMP |
| 7 | `test_oracle_integer_maps_to_int64` | INTEGER -> INT64 |
| 8 | `test_xmltype_is_lossy` | XMLTYPE flagged as lossy |
| 9 | `test_varchar2_is_not_lossy` | VARCHAR2 is safe (not lossy) |
| 10 | `test_unsupported_dialect_raises_value_error` | Unknown dialect raises error |
| 11 | `test_generate_ddl_contains_partition_by` | PARTITION BY clause generated |
| 12 | `test_generate_ddl_contains_cluster_by` | CLUSTER BY clause generated |
| 13 | `test_generate_ddl_contains_correct_types` | BigQuery types used (not Oracle) |
| 14 | `test_generate_ddl_contains_not_null` | NOT NULL constraint included |
| 15 | `test_generate_ddl_table_reference_format` | `project.dataset.table` format correct |
| 16 | `test_adapter_get_dialect_name` | Returns "bigquery" |
| 17 | `test_adapter_not_connected_raises_error` | RuntimeError before connect() |
| 18 | `test_adapter_connect_requires_project_id` | ValueError if project_id missing |
| 19 | `test_adapter_get_type_mapping_returns_dict` | Returns populated dict |
| 20 | `test_adapter_generate_ddl_returns_string` | Returns valid CREATE TABLE string |
| 21 | `test_adapter_connect_via_workload_identity` | (Integration) Live GCP connection works |

---

## Complete End-to-End Flow: All Stories Combined

This is the full lifecycle of how all three user stories connect from start to finish.

```
+=================================================================+
|                    FULL END-TO-END FLOW                          |
+=================================================================+

  [1] DESIGN TIME (TA-01a)
      |
      v
  Define abstract TargetAdapter contract
  Define ColumnProfile & TableProfile schemas
  Constraint: zero database-specific imports
      |
      v
  [2] IMPLEMENTATION TIME (TA-02)
      |
      v
  Build BigQueryAdapter implementing TargetAdapter
      |
      +---> Type Mapping Module
      |     Oracle types --> BigQuery types
      |     Critical: DATE->DATETIME, NUMBER->NUMERIC
      |     Track lossy conversions (XMLTYPE, FLOAT, etc.)
      |
      +---> DDL Generator Module
      |     Schema def + recommendations --> CREATE TABLE SQL
      |     Includes PARTITION BY, CLUSTER BY, NOT NULL, lossy warnings
      |
      +---> Sandbox Lifecycle
      |     connect --> create_sandbox --> deploy_ddl -->
      |     load_test_data --> execute_query -->
      |     get_table_profile --> destroy_sandbox
      |
      v
  [3] VERIFICATION TIME (TA-01b)
      |
      v
  Compliance Harness validates BigQueryAdapter
      |
      v
  +---------------------------------------------------------------+
  | Harness Run Sequence:                                          |
  |                                                                |
  | 1. connect({"project_id": "my-gcp-project"})                   |
  |    --> Workload Identity auth                                  |
  |    --> bigquery.Client created                                 |
  |                                                                |
  | 2. get_dialect_name() --> "bigquery" (check: is str?)          |
  |                                                                |
  | 3. get_type_mapping("oracle") --> {dict} (check: is dict?)     |
  |                                                                |
  | 4. create_sandbox("harness_test")                              |
  |    --> qlift_sandbox_harness_test_a1b2c3d4 (check: is str?)    |
  |                                                                |
  | 5. deploy_ddl(sandbox_id, CREATE TABLE harness_test_table ...) |
  |    --> Table created in sandbox dataset                        |
  |                                                                |
  | 6. load_test_data(sandbox_id, "harness_test_table",            |
  |    [{Alice,100.50}, {Bob,200.75}, {Carol,300.00}])             |
  |    --> 3 rows inserted (check: is int?)                        |
  |                                                                |
  | 7. execute_query(sandbox_id,                                   |
  |    "SELECT * FROM harness_test_table")                         |
  |    --> [{id:1,...}, {id:2,...}, {id:3,...}] (check: is list?)   |
  |                                                                |
  | 8. get_table_profile(sandbox_id, "harness_test_table")         |
  |    --> TableProfile(row_count=3, columns=[...])                |
  |       (check: is TableProfile?)                                |
  |                                                                |
  | 9. destroy_sandbox(sandbox_id)  <-- ALWAYS runs (finally)      |
  |    --> Dataset deleted with all contents                       |
  |                                                                |
  | RESULT: 9/9 PASSED --> Adapter is contract-compliant           |
  +---------------------------------------------------------------+
      |
      v
  [4] PRODUCTION USE
      |
      v
  QLift Verify Service uses BigQueryAdapter via TargetAdapter
  interface. It never knows it's talking to BigQuery.
  Swap to AlloyDB or Spanner by implementing a new adapter.
      |
      v
  END
```

---

## Running the Tests

```bash
# Run all TA-01a tests (contract & schemas)
pytest tests/target/ta01a/test_ta01a.py -v

# Run all TA-01b tests (compliance harness)
pytest tests/target/ta01b/test_ta01b.py -v

# Run all TA-02 tests (BigQuery adapter - unit tests only, no GCP needed)
pytest tests/target/ta02/test_ta02.py -v

# Run TA-02 integration test (requires live GCP project)
GCP_PROJECT_ID=my-project pytest tests/target/ta02/test_ta02.py -v -m integration

# Run ALL tests at once
pytest tests/ -v
```

---

## Summary: What Each Story Delivers

| Story | Deliverable | Key Guarantee |
|-------|-------------|---------------|
| **TA-01a** | Abstract contract + data schemas | Database-agnostic; zero vendor imports |
| **TA-01b** | Compliance harness runner | `destroy_sandbox()` ALWAYS runs; no orphaned resources |
| **TA-02** | BigQuery concrete adapter | `DATE->DATETIME` (no time loss); `NUMBER->NUMERIC` (no precision loss); Workload Identity (no key files) |
