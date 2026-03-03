# QLift Target Module - Demo Presentation Guide
# (Step-by-step script: what to SAY, what to SHOW, what to RUN)

---

## BEFORE YOU START - Preparation Checklist

```
[ ] Open the flowchart file: QLift_Target_E2E_Flowchart_Demo.md
[ ] Open a terminal in the project root (C:\Users\Quadrant\Desktop\Target)
[ ] Activate the virtual environment: venv\Scripts\activate
[ ] Have these files ready to show in your editor:
      - qlift/target/ta01a/adapter.py
      - qlift/target/ta01a/schemas.py
      - qlift/target/ta01b/harness.py
      - qlift/target/ta02/bigquery/type_mapping.py
      - qlift/target/ta02/bigquery/ddl_generator.py
      - qlift/target/ta02/bigquery/adapter.py
```

---

## DEMO STRUCTURE (Total: ~20-25 minutes)

```
  INTRO (2 min)  --->  TA-01a (5 min)  --->  TA-01b (7 min)  --->  TA-02 (8 min)  --->  E2E (3 min)
   "The Problem"       "The Rulebook"        "The Inspector"       "The Worker"         "All Together"
```

---

# PART 1: INTRO - "The Problem" (2 minutes)

## What to SAY:

> "We are building QLift - a platform that migrates databases from Oracle to
> Google BigQuery. The challenge is: how does QLift talk to the target database?
>
> We need three things:
> 1. A RULEBOOK - what methods must every target database support?
> 2. An INSPECTOR - how do we verify an adapter follows the rulebook?
> 3. A WORKER - the actual BigQuery implementation
>
> These map to our three user stories: TA-01a, TA-01b, and TA-02."

## What to SHOW:

Point to the **Architecture Diagram** in the flowchart file:

```
  QLift Verify Service  (top - only knows the abstract contract)
         |
         v
  TA-01a: Contract Layer  (middle - the rulebook)
      /           \
     v              v
  TA-02: BigQuery   TA-01b: Harness
  (the worker)      (the inspector)
```

### KEY POINT to emphasize:
> "The Verify Service at the top NEVER knows it's talking to BigQuery.
> It only talks to the abstract TargetAdapter. This means tomorrow we
> can swap to AlloyDB or Spanner without changing a single line in Verify."

---

# PART 2: TA-01a - "The Rulebook" (5 minutes)

## What to SAY:

> "TA-01a is the foundation. We define TWO things here:
> 1. Data shapes - ColumnProfile and TableProfile
> 2. The abstract contract - TargetAdapter with 10 methods
>
> Think of it like a job description. It says WHAT the adapter must do,
> but NOT HOW. The how comes later in TA-02."

---

### Step 2.1: Show the Data Shapes (1 min)

**OPEN FILE:** `qlift/target/ta01a/schemas.py`

**SAY:**
> "First, we define what data looks like when it comes back from the target.
> A ColumnProfile holds info about one column - its name, type, whether
> it allows nulls, and an optional warning if the type conversion may lose data."

**POINT TO** (lines 8-33):
```
ColumnProfile:
   name              --> "order_date"
   type              --> "DATETIME"
   nullable          --> True/False
   precision_warning --> "NUMBER->FLOAT64 may lose precision" or None
```

**SAY:**
> "A TableProfile wraps the whole table - sandbox ID, table name,
> row count, and a list of ColumnProfiles."

**POINT TO** (lines 37-63):
```
TableProfile:
   sandbox_id  --> "qlift_sandbox_abc123"
   table_name  --> "orders"
   row_count   --> 5000
   columns     --> [ColumnProfile, ColumnProfile, ...]
```

---

### Step 2.2: Show the Abstract Contract (2 min)

**OPEN FILE:** `qlift/target/ta01a/adapter.py`

**SAY:**
> "This is the rulebook. TargetAdapter is an abstract class.
> You CANNOT create an instance of it directly. You must implement
> all 10 methods. Let me walk through them in order."

**POINT TO each method and explain in ONE sentence each:**

| Method | Point to line | Say this |
|--------|---------------|----------|
| `connect()` | Line 21 | "Log into the target database using config dict" |
| `get_dialect_name()` | Line 35 | "Return a simple string like 'bigquery' or 'alloydb'" |
| `get_grammar()` | Line 45 | "Return SQL grammar rules so the validator can check translated SQL" |
| `get_type_mapping()` | Line 56 | "Return a dictionary mapping source types to target types" |
| `create_sandbox()` | Line 75 | "Create a temporary isolated test environment - returns a unique ID" |
| `destroy_sandbox()` | Line 91 | "Delete the sandbox - MUST always be called, even if tests fail" |
| `deploy_ddl()` | Line 105 | "Run CREATE TABLE or CREATE VIEW inside the sandbox" |
| `load_test_data()` | Line 120 | "Insert test rows into a sandbox table - returns row count" |
| `execute_query()` | Line 144 | "Run a SELECT query and return results as list of dicts" |
| `get_table_profile()` | Line 166 | "Collect statistics like row count and column metadata" |
| `generate_ddl()` | Line 185 | "Generate a CREATE TABLE statement for the target database" |

---

### Step 2.3: Prove it Works - Run Tests (2 min)

**SAY:**
> "Let me prove two things. First, you cannot use TargetAdapter directly.
> Second, the data schemas store values correctly."

**RUN in terminal:**
```bash
pytest tests/target/ta01a/test_ta01a.py -v
```

**EXPECTED OUTPUT (point to each line):**
```
test_target_adapter_raises_type_error             PASSED  <-- "Can't instantiate"
test_table_profile_columns_returns_list_of_...    PASSED  <-- "Columns work"
test_column_profile_stores_values_correctly        PASSED  <-- "Fields stored"
test_column_profile_precision_warning_can_be_none  PASSED  <-- "None works"
test_no_bigquery_imports_in_contract_files          PASSED  <-- "Zero SDK imports!"
test_table_profile_stores_row_count                PASSED  <-- "Row count works"
```

**SAY for the ZERO imports test:**
> "This test is important! It scans the actual source code of adapter.py
> and schemas.py and checks that ZERO google.cloud imports exist.
> This guarantees the contract stays database-agnostic.
> If someone accidentally adds a BigQuery import here, this test BREAKS."

---

### TA-01a TRANSITION:

> "So now we have the rulebook. But how do we KNOW that an adapter
> actually follows it? That's TA-01b - the compliance harness."

---

# PART 3: TA-01b - "The Inspector" (7 minutes)

## What to SAY:

> "TA-01b is our quality inspector. It takes ANY adapter - BigQuery,
> AlloyDB, a mock - and runs all 9 contract methods in order.
> For each method, it checks: did it return the right type?
> Did it crash? And critically: did we clean up the sandbox?"

---

### Step 3.1: Show the Harness Flow (2 min)

**OPEN FILE:** `qlift/target/ta01b/harness.py`

**Point to the flowchart section "TA-01b Full Flowchart" in the demo file.**

**SAY:**
> "The harness runs 9 steps in order. I want you to notice THREE things:
>
> ONE - Every step is wrapped in its own try/except. If step 3 fails,
> step 4 still runs. We don't stop early.
>
> TWO - The return type is checked. If execute_query returns a string
> instead of a list, it's caught and reported as FAIL.
>
> THREE - Look at the FINALLY block at the bottom..."

**POINT TO lines 146-160:**
> "destroy_sandbox lives in a FINALLY block. This means even if
> deploy_ddl crashes, even if load_test_data throws an error,
> destroy_sandbox ALWAYS runs. Why? Because an orphaned BigQuery
> dataset costs real money and violates GCP governance."

**Draw this picture with your hand/cursor on the flowchart:**
```
   Steps 1-8 (TRY)         Step 9 (FINALLY)
   ┌─────────────┐          ┌─────────────┐
   │ connect     │          │             │
   │ dialect     │          │  destroy    │
   │ mapping     │  CRASH!  │  sandbox    │
   │ sandbox  ───┼──────────>             │
   │ ddl         │          │  ALWAYS     │
   │ load        │          │  RUNS       │
   │ query       │          │             │
   │ profile     │          └─────────────┘
   └─────────────┘
```

---

### Step 3.2: Live Demo - Three Scenarios (3 min)

**SAY:**
> "Let me show you three scenarios to prove this works."

**RUN in terminal:**
```bash
pytest tests/target/ta01b/test_ta01b.py -v
```

**Walk through the output, highlighting these THREE tests:**

#### Scenario A: Good Adapter (all PASS)
**POINT TO:** `test_good_adapter_all_pass → PASSED`

**SAY:**
> "GoodMockAdapter implements every method correctly.
> The harness runs all 9 steps, all return the right types.
> Result: 9/9 PASSED."

#### Scenario B: Bad Return Type (FAIL detected)
**POINT TO:** `test_bad_adapter_execute_query_reports_fail → PASSED`

**SAY:**
> "BadMockAdapter returns a STRING from execute_query instead of a LIST.
> The harness catches this and reports: FAIL - expected list, got str.
> This is how we catch bugs in adapter implementations."

#### Scenario C: Crash Mid-Run (sandbox STILL destroyed)
**POINT TO:** `test_destroy_sandbox_called_even_after_crash → PASSED`

**SAY:**
> "CrashingMockAdapter throws RuntimeError during deploy_ddl.
> The harness catches it, marks deploy_ddl as FAIL, but the
> FINALLY block still runs destroy_sandbox. No orphaned sandbox.
> We verify this by checking adapter.destroy_called == True."

---

### Step 3.3: Edge Case - Sandbox Never Created (1 min)

**POINT TO:** `test_harness_skips_destroy_when_sandbox_never_created → PASSED`

**SAY:**
> "What if the adapter crashes BEFORE create_sandbox even runs?
> sandbox_id is None. The finally block sees this and shows SKIP
> instead of trying to destroy something that doesn't exist.
> No crash, no error, clean exit."

---

### Step 3.4: CLI Entry Point (1 min)

**POINT TO** lines 183-222 in harness.py:

**SAY:**
> "The harness also has a CLI. You can run it from the terminal:
>
>     python -m qlift.target.ta01b.harness --adapter bigquery --project my-project
>
> It dynamically loads the adapter class using importlib.
> Today we have BigQuery. Tomorrow if we add AlloyDB, we just add
> one entry to the adapter_map and the harness works automatically."

---

### TA-01b TRANSITION:

> "We have the rulebook (TA-01a) and the inspector (TA-01b).
> Now let's look at the actual worker - the BigQuery adapter."

---

# PART 4: TA-02 - "The Worker" (8 minutes)

## What to SAY:

> "TA-02 is where we actually talk to BigQuery. It has three parts:
> 1. Type Mapping - converting Oracle types to BigQuery types
> 2. DDL Generator - building CREATE TABLE statements
> 3. The Adapter - sandbox lifecycle connecting everything"

---

### Step 4.1: Type Mapping - The Two Critical Rules (3 min)

**OPEN FILE:** `qlift/target/ta02/bigquery/type_mapping.py`

**Point to the "Type Mapping Flowchart" in the demo file.**

**SAY:**
> "When we migrate from Oracle to BigQuery, every column type must
> be converted. Most are straightforward: VARCHAR2 becomes STRING,
> BLOB becomes BYTES. But there are TWO critical rules that prevent
> silent data loss."

**CRITICAL RULE 1 - Point to line 47:**

**SAY (slowly, this is important):**
> "Rule 1: Oracle DATE maps to BigQuery DATETIME, NOT BigQuery DATE.
>
> Why? Oracle DATE stores BOTH date AND time: 2024-01-15 14:32:00.
> BigQuery DATE only stores the date part: 2024-01-15.
>
> If we mapped DATE to DATE, we would SILENTLY LOSE the time component.
> A 2pm order would look like it happened at midnight.
> Financial auditors would flag this. So we map to DATETIME."

**CRITICAL RULE 2 - Point to line 36:**

**SAY (slowly):**
> "Rule 2: Oracle NUMBER maps to BigQuery NUMERIC, NOT BigQuery FLOAT64.
>
> Why? Oracle NUMBER has exact decimal precision: 99.99 stays 99.99.
> BigQuery FLOAT64 uses floating point: 99.99 becomes 99.98999999...
>
> For financial data, this is unacceptable. A billing system showing
> $99.99 vs $99.98 is a bug. So we map to NUMERIC which preserves
> exact precision."

**LOSSY WARNINGS - Point to lines 64-69:**

**SAY:**
> "Some conversions ARE lossy and we can't avoid it.
> XMLTYPE to JSON may lose XML-specific features.
> FLOAT types may have precision differences.
> For these, we add a precision_warning to the ColumnProfile
> so downstream systems know to be careful."

---

### Step 4.2: DDL Generation (2 min)

**OPEN FILE:** `qlift/target/ta02/bigquery/ddl_generator.py`

**Point to the "DDL Generation Flowchart" in the demo file.**

**SAY:**
> "The DDL generator takes a schema definition and recommendations,
> and outputs a complete BigQuery CREATE TABLE statement.
> Let me walk through the 5 steps."

**Walk through each step pointing at the flowchart:**

> "Step 1: Build the table reference. If we have project and dataset,
> it becomes backtick project.dataset.table backtick.
>
> Step 2: For each column, convert the Oracle type to BigQuery type,
> add NOT NULL if needed, add a warning comment if it's a lossy type.
>
> Step 3: If recommendations include a partition column, add
> PARTITION BY DATE(column). This is how BigQuery optimizes large tables.
>
> Step 4: If recommendations include cluster columns, add
> CLUSTER BY col1, col2. Maximum 4 columns - BigQuery's limit.
>
> Step 5: Assemble everything into the final SQL string."

**SHOW the expected output (point to the flowchart):**
```sql
CREATE TABLE `my-gcp-project.sales.orders`
(
  order_id      NUMERIC  NOT NULL,
  order_date    DATETIME NOT NULL,
  amount        NUMERIC
)
PARTITION BY DATE(order_date)
CLUSTER BY customer_id, status;
```

**SAY:**
> "Notice: order_date is DATETIME not DATE. amount is NUMERIC not FLOAT64.
> The two critical rules are baked into every DDL we generate."

---

### Step 4.3: The BigQuery Adapter (1 min)

**OPEN FILE:** `qlift/target/ta02/bigquery/adapter.py`

**SAY:**
> "BigQueryAdapter implements every method from the TA-01a contract.
> Three quick highlights:
>
> ONE - Authentication uses Workload Identity. No JSON key files.
> Locally you run gcloud auth, in GKE production it's automatic.
>
> TWO - create_sandbox generates a unique BigQuery dataset with a UUID.
> Each test run gets its own isolated dataset.
>
> THREE - destroy_sandbox uses delete_contents=True and not_found_ok=True.
> It deletes everything inside the dataset, and doesn't crash if the
> dataset is already gone. Belt and suspenders."

---

### Step 4.4: Run TA-02 Tests (2 min)

**RUN in terminal:**
```bash
pytest tests/target/ta02/test_ta02.py -v
```

**Walk through key tests in the output:**

| When you see this test... | Say this... |
|---------------------------|-------------|
| `test_oracle_date_maps_to_datetime PASSED` | "Critical Rule 1 verified - DATE goes to DATETIME" |
| `test_oracle_number_maps_to_numeric PASSED` | "Critical Rule 2 verified - NUMBER goes to NUMERIC" |
| `test_xmltype_is_lossy PASSED` | "Lossy detection works - XMLTYPE flagged" |
| `test_generate_ddl_contains_partition_by PASSED` | "PARTITION BY clause is generated correctly" |
| `test_generate_ddl_contains_correct_types PASSED` | "DDL uses BigQuery types, not Oracle types" |
| `test_adapter_not_connected_raises_error PASSED` | "Safety check: must call connect() first" |

---

# PART 5: END-TO-END - "All Together" (3 minutes)

## What to SAY:

> "Let me now show how all three stories connect as one flow."

**Point to the "Complete End-to-End Flow" section in the flowchart.**

**Walk through the 4 phases:**

### Phase 1: Design Time (TA-01a)
> "We start by defining the rulebook. Abstract contract, data schemas.
> Zero database-specific code. This is the foundation everything else builds on."

### Phase 2: Implementation Time (TA-02)
> "Next, we build the BigQuery worker. It implements every method
> from the contract. Type mapping protects against silent data loss.
> DDL generator produces optimized BigQuery tables."

### Phase 3: Verification Time (TA-01b)
> "Then the harness runs all 9 steps against the BigQuery adapter.
> It checks return types, catches wrong implementations, and
> guarantees sandbox cleanup. Result: 9/9 PASSED means the adapter
> is contract-compliant."

### Phase 4: Production
> "In production, the QLift Verify Service imports only TargetAdapter.
> It calls connect(), create_sandbox(), deploy_ddl()... and never knows
> whether BigQuery, AlloyDB, or Spanner is behind it.
> To add a new database, we just implement one new adapter class.
> No changes to the Verify Service. That's the power of the contract pattern."

---

## FINAL RUN: All Tests Together

**SAY:**
> "Let me run all tests across all three stories to prove everything works."

**RUN:**
```bash
pytest tests/ -v
```

**EXPECTED:** All tests pass (approximately 30 tests total).

**SAY:**
> "Every test green. The contract is clean, the harness catches failures,
> the BigQuery adapter passes all checks, and we have zero silent data loss."

---

# HANDLING QUESTIONS

Common questions and prepared answers:

### Q: "Why not just test BigQuery directly? Why the abstract contract?"
> "Because tomorrow we might add AlloyDB or Spanner. With the abstract
> contract, the Verify Service doesn't change at all. We just implement
> a new adapter and run the harness. Plug and play."

### Q: "What if someone adds a new method to TargetAdapter?"
> "They add the abstract method to adapter.py. Every existing adapter
> will immediately break with TypeError (Python enforces this).
> They must implement it in BigQueryAdapter. The harness should also
> be updated to test the new method."

### Q: "Why DATE -> DATETIME and not just DATE?"
> "Oracle DATE stores date AND time: 2024-01-15 14:32:00.
> BigQuery DATE only stores the date: 2024-01-15.
> Mapping DATE to DATE silently drops the time. For financial
> and audit data, this is unacceptable. DATETIME keeps both."

### Q: "Why NUMBER -> NUMERIC and not FLOAT64?"
> "FLOAT64 uses IEEE 754 floating point. 99.99 becomes 99.98999...
> For financial data like billing, payments, accounting - you need
> exact precision. NUMERIC gives you that. FLOAT64 does not."

### Q: "What happens if the GCP connection fails during the harness?"
> "connect() fails with an exception. The harness marks it as FAIL
> and continues through steps 2-8 (which will likely also fail).
> But sandbox_id is still None, so step 9 shows SKIP.
> No crash, no orphan, clean exit."

### Q: "Can I run this without a GCP project?"
> "Yes. All unit tests run locally with zero GCP dependency.
> Only test_adapter_connect_via_workload_identity needs a real project,
> and it auto-skips if GCP_PROJECT_ID env var is not set."

---

# QUICK REFERENCE: Demo Talking Points Cheat Sheet

```
TA-01a (Rulebook):
  - Abstract contract = 10 methods
  - ColumnProfile + TableProfile = data shapes
  - ZERO BigQuery imports in contract
  - "It says WHAT, not HOW"

TA-01b (Inspector):
  - 9 steps in sequence
  - Checks return types
  - FINALLY block = destroy_sandbox ALWAYS runs
  - Three scenarios: good, bad type, crash

TA-02 (Worker):
  - Critical Rule 1: DATE -> DATETIME (not DATE)
  - Critical Rule 2: NUMBER -> NUMERIC (not FLOAT64)
  - DDL: PARTITION BY + CLUSTER BY
  - Auth: Workload Identity (no key files)
  - Sandbox: create -> use -> destroy (always)

E2E:
  - Design -> Implement -> Verify -> Production
  - Swap databases by implementing one new class
  - Verify Service never knows which database is behind it
```
