# QLift Target Module - Simple Flowchart
# (Easy to understand for everyone)

---

## What is QLift doing?

```
  Moving data from ORACLE (old database) ---> BIGQUERY (new database)
```

That's it. But we need to do it **safely** without losing any data.

---

## The 3 Pieces (User Stories)

```
  +----------------+       +----------------+       +----------------+
  |   TA-01a       |       |   TA-02        |       |   TA-01b       |
  |   THE RULEBOOK |       |   THE WORKER   |       |   THE CHECKER  |
  |                |       |                |       |                |
  |  "What to do"  | ----> | "Does the work"| ----> | "Did it right?"|
  +----------------+       +----------------+       +----------------+
```

---

## STORY 1: TA-01a - The Rulebook

**One line:** A list of 10 things every database adapter MUST be able to do.

```
  THE RULEBOOK says every adapter must do these 10 things:

  +-----------------------------------------------------+
  |                                                     |
  |   1.  Connect          - Log in to the database     |
  |   2.  Get Dialect      - Say your name ("bigquery") |
  |   3.  Get Grammar      - Share your SQL rules       |
  |   4.  Get Type Map     - How to convert data types  |
  |   5.  Create Sandbox   - Make a safe test area      |
  |   6.  Destroy Sandbox  - Clean up the test area     |
  |   7.  Deploy DDL       - Create tables              |
  |   8.  Load Test Data   - Put test rows in           |
  |   9.  Execute Query    - Run a SELECT query         |
  |  10.  Get Table Profile- Get table stats            |
  |                                                     |
  +-----------------------------------------------------+

  RULE: No database-specific code allowed here.
        This rulebook works for ANY database.
```

---

## STORY 2: TA-02 - The Worker (BigQuery)

**One line:** The actual code that talks to Google BigQuery, following the rulebook.

### How data types get converted:

```
       ORACLE (source)              BIGQUERY (target)
      +--------------+            +--------------+
      |  VARCHAR2    |  -------->  |  STRING      |
      |  NUMBER      |  -------->  |  NUMERIC     |  <-- NOT FLOAT64 (keeps exact numbers)
      |  DATE        |  -------->  |  DATETIME    |  <-- NOT DATE (keeps the time part)
      |  TIMESTAMP   |  -------->  |  TIMESTAMP   |
      |  BLOB        |  -------->  |  BYTES       |
      |  CLOB        |  -------->  |  STRING      |
      |  INTEGER     |  -------->  |  INT64       |
      |  XMLTYPE     |  -------->  |  JSON        |  <-- WARNING: may lose some data
      +--------------+            +--------------+
```

### Why these 2 rules matter:

```
  RULE 1: Oracle DATE ---> BigQuery DATETIME (not DATE)

      Oracle stores:    2024-01-15 14:32:00  (date + time)
      BQ DATE stores:   2024-01-15           (date only - TIME IS LOST!)
      BQ DATETIME:      2024-01-15 14:32:00  (date + time - SAFE!)

  -----------------------------------------------------------

  RULE 2: Oracle NUMBER ---> BigQuery NUMERIC (not FLOAT64)

      Oracle stores:    $99.99               (exact)
      BQ FLOAT64:       $99.98999...         (wrong! money is off)
      BQ NUMERIC:       $99.99              (exact - SAFE!)
```

### How a table gets created:

```
  INPUT (what we know):                 OUTPUT (what BigQuery gets):
  +-------------------------+           +----------------------------------+
  | Table: orders           |           | CREATE TABLE `project.sales.orders`
  | Columns:                |           | (                                |
  |   order_id  (NUMBER)    |  ------>  |   order_id   NUMERIC  NOT NULL,  |
  |   order_date (DATE)     |           |   order_date DATETIME NOT NULL,  |
  |   amount    (NUMBER)    |           |   amount     NUMERIC             |
  | Partition: order_date   |           | )                                |
  | Cluster: customer_id    |           | PARTITION BY DATE(order_date)    |
  +-------------------------+           | CLUSTER BY customer_id;          |
                                        +----------------------------------+
```

---

## STORY 3: TA-01b - The Checker (Compliance Harness)

**One line:** Runs all 9 checks on any adapter to make sure it follows the rulebook.

### The checking process:

```
  START
    |
    v
  Step 1: Can it CONNECT?
    |  Yes --> PASS     No --> FAIL
    v
  Step 2: Does it return a DIALECT NAME?
    |  Yes (string) --> PASS     No --> FAIL
    v
  Step 3: Does it return a TYPE MAP?
    |  Yes (dictionary) --> PASS     No --> FAIL
    v
  Step 4: Can it CREATE a SANDBOX?
    |  Yes (returns ID) --> PASS     No --> FAIL
    v
  Step 5: Can it CREATE TABLES in the sandbox?
    |  Yes --> PASS     No --> FAIL
    v
  Step 6: Can it LOAD TEST DATA?
    |  Yes (returns count) --> PASS     No --> FAIL
    v
  Step 7: Can it RUN A QUERY?
    |  Yes (returns rows) --> PASS     No --> FAIL
    v
  Step 8: Can it GET TABLE STATS?
    |  Yes (returns profile) --> PASS     No --> FAIL
    v
  Step 9: CLEANUP - Destroy the sandbox  *** ALWAYS RUNS ***
    |  Sandbox exists? --> Destroy it --> PASS
    |  No sandbox?     --> SKIP (that's OK)
    v
  DONE --> Show results: X/9 PASSED
```

### The safety guarantee:

```
  WHAT IF SOMETHING CRASHES?

  Normal flow:             Crash flow:

  Step 1  PASS             Step 1  PASS
  Step 2  PASS             Step 2  PASS
  Step 3  PASS             Step 3  PASS
  Step 4  PASS             Step 4  PASS
  Step 5  PASS             Step 5  CRASH!
  Step 6  PASS               |
  Step 7  PASS               |  (skips to cleanup)
  Step 8  PASS               |
     |                       |
     v                       v
  Step 9  CLEANUP          Step 9  CLEANUP  <-- STILL RUNS!
     |                       |
     v                       v
  All clean!               All clean! (no orphaned resources)
```

---

## The Big Picture - How Everything Connects

```
  +------------------------------------------------------------------+
  |                         QLift Platform                            |
  +------------------------------------------------------------------+
       |
       |  asks: "Hey, do something with the target database"
       |
       v
  +------------------------------------------------------------------+
  |              TA-01a: THE RULEBOOK                                 |
  |                                                                  |
  |  "I don't care WHICH database. Here are the 10 things            |
  |   any adapter must do."                                          |
  +------------------------------------------------------------------+
       |                                    |
       |  implements                        |  tests against
       v                                    v
  +-----------------------------+    +-----------------------------+
  |  TA-02: THE WORKER          |    |  TA-01b: THE CHECKER        |
  |  (BigQuery)                 |    |                             |
  |                             |    |  Runs 9 checks:            |
  |  - Converts Oracle types    |    |    connect?       PASS     |
  |  - Builds CREATE TABLE SQL  |--->|    dialect?        PASS     |
  |  - Manages sandboxes        |    |    type map?       PASS     |
  |  - Runs queries             |    |    sandbox?        PASS     |
  |  - Cleans up                |    |    tables?         PASS     |
  |                             |    |    load data?      PASS     |
  |                             |    |    query?          PASS     |
  |                             |    |    profile?        PASS     |
  |                             |    |    cleanup?        PASS     |
  |                             |    |                             |
  |                             |    |  Result: 9/9 PASSED!       |
  +-----------------------------+    +-----------------------------+
```

---

## Want to add a NEW database tomorrow?

```
  TODAY:                              TOMORROW:

  Rulebook (TA-01a)  --> same         Rulebook (TA-01a)  --> NO CHANGE
  Checker  (TA-01b)  --> same         Checker  (TA-01b)  --> NO CHANGE
  Worker   (TA-02)   --> BigQuery     Worker   (TA-02)   --> BigQuery
                                      Worker   (NEW)     --> AlloyDB  <-- just add this!
```

**That's the power of this design. One new file = one new database supported.**

---

## Quick Summary

| Story | Role | One-liner |
|-------|------|-----------|
| TA-01a | Rulebook | "Here's what every adapter must do" |
| TA-02 | Worker | "Here's how BigQuery actually does it" |
| TA-01b | Checker | "Let me verify it was done correctly" |

| Critical Rule | Why |
|---------------|-----|
| DATE --> DATETIME | Don't lose the time (2:30 PM matters!) |
| NUMBER --> NUMERIC | Don't lose the cents ($99.99, not $99.98) |
| Sandbox ALWAYS cleaned up | Don't waste money on orphaned resources |
