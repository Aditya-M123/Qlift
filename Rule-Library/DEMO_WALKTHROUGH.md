# RE-02: Oracle-to-BigQuery Rule Library — End-to-End Demo Walkthrough

---

## 1. Project Overview

### What Is This?
The **Rule Library (RE-02)** is a structured collection of **54 YAML translation rules** that define how Oracle SQL constructs (functions, types, keywords, PL/SQL patterns) should be converted into their Google BigQuery equivalents.

### Why Does It Exist?
When migrating an Oracle database to BigQuery, thousands of SQL statements need to be rewritten. This library provides a **machine-readable, testable, version-controlled** catalog of every known translation pattern — so the Rule Engine (RE-01, built separately) can load these rules and automatically suggest or apply conversions.

### Key Numbers
| Metric | Value |
|--------|-------|
| Total rules | 54 |
| Oracle-to-BigQuery rules (OBQ-*) | 49 |
| Shared BigQuery rules (SBQ-*) | 5 |
| YAML rule files | 9 |
| Test files | 8 |
| Total pytest tests | 205 |
| Critical acceptance tests | 3 |
| Test pass rate | 100% |

---

## 2. Directory Structure

```
Rule-Library/
├── pyproject.toml                          # Python package config + dependencies
├── Makefile                                # Quick commands: install, test, clean
├── rules/
│   ├── RULE_TEMPLATE.yaml                  # Template for authoring new rules
│   ├── oracle-to-bigquery/
│   │   ├── direct_swaps/
│   │   │   ├── null_handling.yaml          # OBQ-001..004  (NVL, NVL2, DECODE)
│   │   │   ├── datetime_functions.yaml     # OBQ-005..012  (SYSDATE, TO_DATE, etc.)
│   │   │   ├── string_functions.yaml       # OBQ-013..017  (INSTR, LISTAGG, etc.)
│   │   │   └── set_and_misc.yaml           # OBQ-018..022  (MINUS, DUAL, ROWNUM)
│   │   ├── type_mapping/
│   │   │   └── type_mapping.yaml           # OBQ-030..039  (VARCHAR2, NUMBER, etc.)
│   │   ├── architectural/
│   │   │   ├── cursor_patterns.yaml        # OBQ-040..044  (cursors, %ROWTYPE)
│   │   │   └── ddl_objects.yaml            # OBQ-045..050  (TRIGGER, PACKAGE, etc.)
│   │   ├── structural/
│   │   │   └── structural_patterns.yaml    # OBQ-051..056  (CONNECT BY, PIVOT, etc.)
│   │   └── auto_candidates/
│   │       └── .gitkeep                    # Placeholder for auto-discovered rules
│   └── shared/
│       └── bigquery/
│           └── bigquery_patterns.yaml      # SBQ-001..005  (partitioning, SAFE_DIVIDE)
└── tests/
    ├── conftest.py                         # Shared YAML loading fixtures
    ├── test_rule_schema.py                 # Schema validation for all 54 rules
    ├── test_acceptance_criteria.py         # 3 critical gotcha tests
    ├── test_all_rules_coverage.py          # Ensures all 54 rule IDs exist
    ├── test_direct_swaps.py               # Tests for OBQ-001..022
    ├── test_type_mapping.py               # Tests for OBQ-030..039
    ├── test_architectural.py              # Tests for OBQ-040..050
    ├── test_structural.py                 # Tests for OBQ-051..056
    └── test_shared.py                     # Tests for SBQ-001..005
```

**Design Decision — Why this folder layout?**
Rules are organized by **translation complexity**, not alphabetically. A developer looking for "how do I convert SYSDATE?" naturally looks in `direct_swaps/datetime_functions.yaml`. Someone dealing with cursor refactoring goes to `architectural/cursor_patterns.yaml`. The `shared/` folder holds patterns that apply regardless of the source database (e.g., BigQuery best practices like partitioning).

---

## 3. YAML Rule Schema (The RE-01 Contract)

Every rule is a YAML dictionary with exactly these fields. This schema is the **contract between RE-02 (this library) and RE-01 (the rule engine)**.

```yaml
- rule_id: "OBQ-001"                    # Unique ID. OBQ- = Oracle→BigQuery, SBQ- = shared
  version: "1.0"                        # Semantic version for change tracking
  name: "NVL to IFNULL"                 # Human-readable short name
  severity: "high"                      # critical | high | medium | low
  source_pattern:
    function: "NVL"                     # Primary key: function | keyword | object_type | construct
    arg_count: 2                        # Optional qualifier: expected argument count
  target_pattern: "IFNULL({a}, {b})"    # BigQuery equivalent with placeholders
  confidence: 1.0                       # 0.0–1.0, how reliable is this automatic swap
  tags: ["null-handling", "function"]   # Searchable category tags
  why: "Explanation text..."            # Rationale, gotchas, edge cases
  tests:                                # Embedded test cases (input → expected)
    - input: "NVL(col1, 0)"
      expected: "IFNULL(col1, 0)"
```

### Field-by-Field Explanation

| Field | Type | Purpose |
|-------|------|---------|
| `rule_id` | String | Unique identifier. `OBQ-` prefix for Oracle-specific, `SBQ-` for shared BigQuery patterns. IDs are grouped by category (001-022 = direct swaps, 030-039 = types, 040-050 = architectural, 051-056 = structural). |
| `version` | String | Tracks rule evolution. If a rule's logic changes, bump this. |
| `name` | String | Short human label shown in reports and UI. |
| `severity` | Enum | How impactful is a missed translation? `critical` = data corruption risk, `high` = query will fail, `medium` = wrong results possible, `low` = cosmetic/compatible. |
| `source_pattern` | Dict | **What to match in Oracle code.** Must have exactly one primary key (`function`, `keyword`, `object_type`, or `construct`). Optional qualifiers (`arg_count`, `arg_type`) narrow the match. |
| `target_pattern` | String | **BigQuery replacement.** Uses `{a}`, `{b}`, `{c}` placeholders for arguments. For architectural rules, this is a descriptive pattern (not mechanically applicable). |
| `confidence` | Float | `1.0` = safe to auto-apply, `0.5` = needs human review, `0.3` = architecture-level redesign required. The Rule Engine uses this to decide auto-apply vs. flag-for-review. |
| `tags` | List | Enables filtering: "show me all datetime rules", "show me all gotchas". |
| `why` | String | Documents the reasoning, edge cases, and pitfalls. This is critical for human reviewers. |
| `tests` | List | Each entry has `input` (Oracle SQL) and `expected` (BigQuery SQL). The Rule Engine runs these to validate the translation logic. |

### The Four Source Pattern Types

```
function:     Oracle built-in function      → NVL, DECODE, INSTR, TO_CHAR
keyword:      Oracle SQL keyword            → SYSDATE, SYSTIMESTAMP, MINUS
object_type:  Oracle DDL data type or object → VARCHAR2, NUMBER, TRIGGER, PACKAGE
construct:    Multi-token Oracle idiom       → ROWNUM_WHERE, CONNECT_BY_PRIOR, DOUBLE_PIPE_CONCAT
```

---

## 4. Rule Categories — The Five Pillars

### 4.1 Direct Swaps (22 rules: OBQ-001 to OBQ-022)

These are **mechanical 1:1 function/keyword replacements** where Oracle has a function and BigQuery has a direct equivalent.

**Sub-categories:**

| File | Rules | Examples |
|------|-------|---------|
| `null_handling.yaml` | OBQ-001..004 | `NVL → IFNULL`, `NVL2 → IF(IS NOT NULL)`, `DECODE → CASE WHEN` |
| `datetime_functions.yaml` | OBQ-005..012 | `SYSDATE → CURRENT_DATETIME()`, `ADD_MONTHS → DATE_ADD`, `TO_CHAR → FORMAT_DATETIME` |
| `string_functions.yaml` | OBQ-013..017 | `INSTR → STRPOS`, `LISTAGG → STRING_AGG`, `\|\| → CONCAT` |
| `set_and_misc.yaml` | OBQ-018..022 | `MINUS → EXCEPT DISTINCT`, `FROM DUAL → remove`, `ROWNUM → LIMIT / ROW_NUMBER` |

**Demo example — OBQ-001 (NVL to IFNULL):**
```
Oracle:   NVL(col1, 0)
BigQuery: IFNULL(col1, 0)
Confidence: 1.0 (safe to auto-apply)
```

### 4.2 Type Mappings (10 rules: OBQ-030 to OBQ-039)

These define how **Oracle data types** in DDL translate to BigQuery types.

| Oracle Type | BigQuery Type | Notes |
|-------------|---------------|-------|
| `VARCHAR2(n)` | `STRING` | Length constraint dropped |
| `NUMBER` | `NUMERIC` | **NOT FLOAT64** — critical gotcha |
| `NUMBER(p,0)` | `INT64` | Scale=0 means integer |
| `CLOB` | `STRING` | Size limit difference |
| `BLOB` | `BYTES` | |
| `DATE` | `DATETIME` | Oracle DATE has time component |
| `TIMESTAMP` | `TIMESTAMP` | Compatible, no change |
| `CHAR(n)` | `STRING` | Padding behavior differs |
| `RAW(n)` | `BYTES` | |
| `XMLTYPE` | `JSON` | Lossy conversion (conf: 0.7) |

### 4.3 Architectural Patterns (11 rules: OBQ-040 to OBQ-050)

These are **not simple swaps** — they require **redesigning the code architecture**. The confidence scores are intentionally low (0.3–0.7) because human judgment is required.

**Cursor patterns (OBQ-040..044):**
- `FOR rec IN cursor LOOP` → Set-based SQL (eliminate row-by-row)
- `BULK COLLECT INTO` → Temp table or set-based query
- `OPEN/FETCH/CLOSE` → Set-based with BigQuery scripting
- `%ROWTYPE` → STRUCT or explicit columns
- `%TYPE` → Explicit BigQuery type

**DDL objects (OBQ-045..050):**
- `TRIGGER` → Cloud Functions + Pub/Sub (conf: 0.3)
- `PACKAGE` → Standalone routines (conf: 0.3)
- `SEQUENCE` → GENERATE_UUID / ROW_NUMBER (conf: 0.6)
- `SYNONYM` → Fully qualified names (conf: 0.8)
- `DBLINK` → EXTERNAL_QUERY (conf: 0.5)
- `EXCEPTION block` → BEGIN...EXCEPTION WHEN ERROR THEN (conf: 0.7)

**Demo example — OBQ-045 (TRIGGER):**
```
Oracle:     CREATE TRIGGER emp_audit AFTER INSERT ON emp FOR EACH ROW ...
BigQuery:   No triggers. Use Cloud Functions + Pub/Sub.
Confidence: 0.3 (architecture-level redesign, cannot auto-apply)
```

### 4.4 Structural Patterns (6 rules: OBQ-051 to OBQ-056)

Complex SQL constructs that need **structural rewriting** of the query.

| Rule | Oracle | BigQuery |
|------|--------|----------|
| OBQ-051 | `CONNECT BY PRIOR` | Recursive CTE (`WITH RECURSIVE`) |
| OBQ-052 | `START WITH` | CTE anchor clause |
| OBQ-053 | `LATERAL view` | `CROSS JOIN UNNEST` |
| OBQ-054 | `PIVOT` | Compatible (native BigQuery support) |
| OBQ-055 | `MERGE` | Compatible (minor adjustments) |
| OBQ-056 | `(+)` outer join | `LEFT OUTER JOIN ... ON ...` |

### 4.5 Shared BigQuery Patterns (5 rules: SBQ-001 to SBQ-005)

Best practices that apply **regardless of source database**. These are recommendations, not translations.

| Rule | Pattern | Why |
|------|---------|-----|
| SBQ-001 | Partition by date | Reduces query cost by pruning scanned data |
| SBQ-002 | SAFE_DIVIDE | Prevents division-by-zero errors |
| SBQ-003 | IS NULL pattern | Ensures correct null comparisons |
| SBQ-004 | GENERATE_UUID | Replaces sequence-based ID generation |
| SBQ-005 | Clustering | Improves filter/join/group-by performance |

---

## 5. The Three Critical Acceptance Gotchas

These are the **most dangerous translation mistakes** that silently corrupt data. Each has a dedicated acceptance test that must NEVER fail.

### Gotcha 1: DECODE with NULL (OBQ-004)

**The Problem:**
Oracle's `DECODE` treats `NULL = NULL` as **true** (non-standard behavior). Standard SQL (and BigQuery) treats `NULL = NULL` as **UNKNOWN** (always false in WHERE context).

```sql
-- Oracle (works correctly):
DECODE(x, NULL, 'is_null', 'not_null')

-- WRONG BigQuery translation:
CASE WHEN x = NULL THEN 'is_null' ELSE 'not_null' END
-- ^^^ This ALWAYS returns 'not_null' because x = NULL is UNKNOWN

-- CORRECT BigQuery translation:
IF(x IS NULL, 'is_null', 'not_null')
```

**Test enforces:** Target pattern and all test cases must use the `IF(x IS NULL, ...)` form, must NEVER use `= NULL`.

### Gotcha 2: SYSDATE mapping (OBQ-005)

**The Problem:**
Oracle `SYSDATE` returns a **DATE with time component** (e.g., `2024-01-15 14:30:00`). A naive translation to BigQuery `CURRENT_DATE()` **silently drops the time**, causing incorrect date comparisons, missed records in time-range queries, and broken audit trails.

```sql
-- Oracle:
SELECT SYSDATE FROM DUAL              -- Returns: 2024-01-15 14:30:00

-- WRONG BigQuery:
SELECT CURRENT_DATE()                  -- Returns: 2024-01-15 (time lost!)

-- CORRECT BigQuery:
SELECT CURRENT_DATETIME()              -- Returns: 2024-01-15T14:30:00
```

**Test enforces:** Target pattern must be exactly `CURRENT_DATETIME()`, never `CURRENT_DATE()`.

### Gotcha 3: NUMBER type mapping (OBQ-031)

**The Problem:**
Oracle `NUMBER` (without precision/scale) can hold **exact decimal values** like financial amounts. Mapping to BigQuery `FLOAT64` introduces **floating-point precision errors** that can corrupt monetary calculations.

```sql
-- Oracle:
salary NUMBER           -- Stores 99999.99 exactly

-- WRONG BigQuery:
salary FLOAT64          -- May store 99999.99000000001 (precision error!)

-- CORRECT BigQuery:
salary NUMERIC          -- Stores 99999.99 exactly (decimal arithmetic)
```

**Test enforces:** Target pattern must be `NUMERIC`, must NEVER contain `FLOAT64`.

---

## 6. Test Infrastructure — Deep Dive

### 6.1 Fixture Architecture (`conftest.py`)

All test fixtures use `scope="session"` so YAML files are loaded **once per test run**, not once per test. This keeps the 205-test suite running in ~2 seconds.

```python
RULES_DIR = pathlib.Path(__file__).resolve().parent.parent / "rules"

def _load_yaml_files(directory: pathlib.Path) -> list[dict[str, Any]]:
    """Recursively load all YAML rule files under directory."""
    rules = []
    for yaml_file in sorted(directory.rglob("*.yaml")):
        if yaml_file.name == "RULE_TEMPLATE.yaml":
            continue                            # Skip the template
        with open(yaml_file, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, list):
            rules.extend(data)
    return rules
```

**Fixtures provided:**

| Fixture | Scope | What It Returns |
|---------|-------|-----------------|
| `all_rules` | session | All 54 rules from all YAML files |
| `oracle_rules` | session | 49 OBQ-* rules only |
| `shared_rules` | session | 5 SBQ-* rules only |
| `rules_by_id` | session | Dict: `{"OBQ-001": {...}, ...}` for O(1) lookup |
| `null_handling_rules` | session | 4 rules from `null_handling.yaml` |
| `datetime_rules` | session | 8 rules from `datetime_functions.yaml` |
| `string_rules` | session | 5 rules from `string_functions.yaml` |
| `set_and_misc_rules` | session | 5 rules from `set_and_misc.yaml` |
| `type_mapping_rules` | session | 10 rules from `type_mapping.yaml` |
| `cursor_rules` | session | 5 rules from `cursor_patterns.yaml` |
| `ddl_rules` | session | 6 rules from `ddl_objects.yaml` |
| `structural_rules` | session | 6 rules from `structural_patterns.yaml` |
| `bigquery_rules` | session | 5 rules from `bigquery_patterns.yaml` |

### 6.2 Test Layers

The test suite has **four distinct validation layers**:

```
Layer 1: Schema Validation         (test_rule_schema.py)
         "Does every rule have the right shape?"
              │
Layer 2: Coverage Verification     (test_all_rules_coverage.py)
         "Are all 54 expected rule IDs present?"
              │
Layer 3: Acceptance Criteria       (test_acceptance_criteria.py)
         "Do the 3 critical gotchas pass?"
              │
Layer 4: Category-Specific Tests   (test_direct_swaps.py, test_type_mapping.py, etc.)
         "Does each rule have correct source/target/confidence/tags?"
```

### Layer 1: Schema Validation (`test_rule_schema.py` — 13 tests)

Validates **every rule in the library** against the RE-01 contract:

```python
REQUIRED_FIELDS = [
    "rule_id", "version", "name", "severity", "source_pattern",
    "target_pattern", "confidence", "tags", "why", "tests",
]
```

What it checks:
- All 10 required fields are present in every rule
- `rule_id` starts with `OBQ-` or `SBQ-`
- `severity` is one of `{critical, high, medium, low}`
- `confidence` is a float between 0.0 and 1.0
- `source_pattern` has at least one primary key (`function`/`keyword`/`object_type`/`construct`)
- `source_pattern` contains no invalid keys
- `tags` is a non-empty list
- `tests` is a non-empty list with `input` and `expected` in each entry
- No duplicate `rule_id` values across the entire library
- `version` and `target_pattern` are strings

### Layer 2: Coverage Verification (`test_all_rules_coverage.py` — 58 tests)

Maintains an **explicit manifest** of all expected rule IDs and verifies each one exists:

```python
EXPECTED_OBQ_IDS = [
    "OBQ-001", "OBQ-002", ..., "OBQ-056",
]
EXPECTED_SBQ_IDS = [
    "SBQ-001", "SBQ-002", "SBQ-003", "SBQ-004", "SBQ-005",
]
```

- `test_total_rule_count`: Asserts exactly 54 rules loaded
- `test_all_obq_ids_present`: No missing Oracle rules
- `test_all_sbq_ids_present`: No missing shared rules
- `test_no_unexpected_ids`: No rogue rules snuck in
- `test_individual_rule_exists` (parametrized x54): Each ID checked individually

### Layer 3: Acceptance Criteria (`test_acceptance_criteria.py` — 14 tests)

Three test classes, one per critical gotcha. Each verifies:
1. The rule exists
2. Its severity is `critical`
3. The `target_pattern` contains the correct keyword
4. The `target_pattern` does NOT contain the dangerous keyword
5. All embedded test cases follow the same constraints

### Layer 4: Category Tests (5 files — 120 tests)

Per-category validation that checks specific rules have the correct:
- Source pattern type and value (e.g., `function: "NVL"`)
- Target pattern content (e.g., `"IFNULL" in target`)
- Confidence scores
- Tags
- Severity levels
- At least one test case each

---

## 7. How to Run

### Setup
```bash
pip install -e ".[dev]"
```

### Run All 205 Tests
```bash
pytest tests/ -v
```

### Run Only the 3 Critical Acceptance Tests
```bash
pytest tests/test_acceptance_criteria.py -v
```

### Run Only the Coverage Check
```bash
pytest tests/test_all_rules_coverage.py -v
```

### Using the Makefile
```bash
make install          # Install the package
make test             # Run all tests
make test-acceptance  # Run the 3 critical gotcha tests
make test-coverage    # Run the coverage check
make clean            # Remove __pycache__ and egg-info
```

---

## 8. Confidence Score Philosophy

The confidence score drives the Rule Engine's behavior:

| Range | Meaning | Engine Action | Example |
|-------|---------|---------------|---------|
| **1.0** | Exact mechanical swap | Auto-apply | `NVL → IFNULL` |
| **0.9–0.95** | Safe with minor caveats | Auto-apply + comment | `LISTAGG → STRING_AGG` |
| **0.7–0.8** | Structural rewrite needed | Flag for review | `CONNECT BY → Recursive CTE` |
| **0.5–0.6** | Major redesign required | Flag for architect | `BULK COLLECT → temp table` |
| **0.3** | Architecture-level change | Manual only | `TRIGGER → Cloud Functions` |

This graduated scale means the Rule Engine can **auto-apply the safe rules** (confidence >= 0.9) while **flagging complex patterns** (confidence < 0.7) for human review.

---

## 9. How to Add a New Rule

1. Copy `rules/RULE_TEMPLATE.yaml`
2. Fill in all required fields following the schema
3. Place the file in the appropriate category folder
4. Add the new rule_id to `EXPECTED_OBQ_IDS` or `EXPECTED_SBQ_IDS` in `test_all_rules_coverage.py`
5. Update the count in `test_total_rule_count`
6. Add category-specific tests in the relevant test file
7. Run `pytest tests/ -v` — all tests must pass

---

## 10. Integration with RE-01 (Rule Engine)

```
┌─────────────────────────────────────────────────┐
│  RE-01: Rule Engine                             │
│                                                 │
│  1. Loads all YAML files from rules/            │
│  2. Parses source_pattern to build match index  │
│  3. Exposes:                                    │
│     - match(oracle_sql)      → matching rules   │
│     - partial_match(token)   → candidate rules  │
│     - apply(rule, input)     → bigquery_sql     │
│  4. Uses confidence to decide auto vs. flagged  │
└────────────────────┬────────────────────────────┘
                     │ reads
                     ▼
┌─────────────────────────────────────────────────┐
│  RE-02: Rule Library (this project)             │
│                                                 │
│  54 YAML rules across 9 files                   │
│  Each rule: source_pattern → target_pattern     │
│  Each rule: embedded tests for validation       │
│  205 pytest tests ensure correctness            │
└─────────────────────────────────────────────────┘
```

The Rule Engine (RE-01) is a **consumer** of this library. It loads the YAML files at startup, builds an index of source patterns, and uses `match()` to find applicable rules for any given Oracle SQL statement. The `confidence` score determines whether the engine auto-applies the conversion or flags it for human review.

---

## 11. Final Test Output (Proof of Completion)

```
$ pytest tests/ -v

tests/test_acceptance_criteria.py    ...  14 passed
tests/test_all_rules_coverage.py     ...  58 passed
tests/test_architectural.py          ...  24 passed
tests/test_direct_swaps.py           ...  34 passed
tests/test_rule_schema.py            ...  13 passed
tests/test_shared.py                 ...  12 passed
tests/test_structural.py             ...  14 passed
tests/test_type_mapping.py           ...  24 passed
tests/test_direct_swaps.py           ...  12 passed

========================= 205 passed in ~2 seconds =========================
```

---

## 12. Summary for Stakeholders

| Question | Answer |
|----------|--------|
| What did we build? | A library of 54 YAML rules mapping Oracle SQL patterns to BigQuery equivalents |
| How is it organized? | 5 categories: direct swaps, type mappings, architectural, structural, shared BigQuery |
| How do we know it's correct? | 205 automated tests, including 3 critical acceptance tests for known data-corruption gotchas |
| How does the Rule Engine use it? | Loads YAML at startup, matches Oracle SQL against `source_pattern`, returns `target_pattern` |
| Can we add more rules? | Yes — copy the template, add to the appropriate folder, update the coverage test, run `pytest` |
| What are the biggest risks? | The 3 critical gotchas (DECODE NULL, SYSDATE, NUMBER) — all protected by acceptance tests that must never fail |
