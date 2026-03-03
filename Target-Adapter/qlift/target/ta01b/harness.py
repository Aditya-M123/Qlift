# qlift/target/ta01b/harness.py

import argparse
import importlib
from typing import Any, Dict, List

from qlift.target.ta01a.schemas import TableProfile


# ─────────────────────────────────────────────
# Test data used by the harness
# ─────────────────────────────────────────────

TEST_DDL = """
CREATE TABLE IF NOT EXISTS harness_test_table (
    id INTEGER,
    name STRING,
    amount NUMERIC
)
"""

TEST_DATA = [
    {"id": 1, "name": "Alice", "amount": 100.50},
    {"id": 2, "name": "Bob",   "amount": 200.75},
    {"id": 3, "name": "Carol", "amount": 300.00},
]

TEST_QUERY = "SELECT * FROM harness_test_table"

TEST_TABLE = "harness_test_table"


# ─────────────────────────────────────────────
# Type checker helper
# ─────────────────────────────────────────────

def check_type(value: Any, expected_type: type, method_name: str) -> str:
    """
    Check if a value matches the expected type.
    Returns PASS or FAIL with a clear message.
    """
    if isinstance(value, expected_type):
        return f"[PASS] {method_name}"
    else:
        return (
            f"[FAIL] {method_name} — "
            f"expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )


# ─────────────────────────────────────────────
# Main harness runner
# ─────────────────────────────────────────────

def run_harness(adapter, config: dict) -> Dict[str, str]:
    """
    Run all contract methods in sequence against the given adapter.
    Always destroys sandbox at the end — even if something crashes.

    Args:
        adapter: any TargetAdapter implementation
        config: connection config dict

    Returns:
        Dict of method_name → PASS or FAIL message
    """
    results = {}
    sandbox_id = None

    print("\nQLift Target Adapter Compliance Harness")
    print(f"Adapter: {adapter.__class__.__name__}")
    print("=" * 45)

    try:
        # ── Step 1: connect ──────────────────────
        try:
            adapter.connect(config)
            results["connect"] = "[PASS] connect"
        except Exception as e:
            results["connect"] = f"[FAIL] connect — {str(e)}"

        # ── Step 2: get_dialect_name ─────────────
        try:
            name = adapter.get_dialect_name()
            results["get_dialect_name"] = check_type(
                name, str, "get_dialect_name"
            )
        except Exception as e:
            results["get_dialect_name"] = f"[FAIL] get_dialect_name — {str(e)}"

        # ── Step 3: get_type_mapping ─────────────
        try:
            mapping = adapter.get_type_mapping("oracle")
            results["get_type_mapping"] = check_type(
                mapping, dict, "get_type_mapping"
            )
        except Exception as e:
            results["get_type_mapping"] = f"[FAIL] get_type_mapping — {str(e)}"

        # ── Step 4: create_sandbox ───────────────
        try:
            sandbox_id = adapter.create_sandbox("harness_test")
            results["create_sandbox"] = check_type(
                sandbox_id, str, "create_sandbox"
            )
        except Exception as e:
            results["create_sandbox"] = f"[FAIL] create_sandbox — {str(e)}"

        # ── Step 5: deploy_ddl ───────────────────
        try:
            adapter.deploy_ddl(sandbox_id, TEST_DDL)
            results["deploy_ddl"] = "[PASS] deploy_ddl"
        except Exception as e:
            results["deploy_ddl"] = f"[FAIL] deploy_ddl — {str(e)}"

        # ── Step 6: load_test_data ───────────────
        try:
            row_count = adapter.load_test_data(
                sandbox_id, TEST_TABLE, TEST_DATA
            )
            results["load_test_data"] = check_type(
                row_count, int, "load_test_data"
            )
        except Exception as e:
            results["load_test_data"] = f"[FAIL] load_test_data — {str(e)}"

        # ── Step 7: execute_query ────────────────
        try:
            rows = adapter.execute_query(sandbox_id, TEST_QUERY)
            results["execute_query"] = check_type(
                rows, list, "execute_query"
            )
        except Exception as e:
            results["execute_query"] = f"[FAIL] execute_query — {str(e)}"

        # ── Step 8: get_table_profile ────────────
        try:
            profile = adapter.get_table_profile(sandbox_id, TEST_TABLE)
            results["get_table_profile"] = check_type(
                profile, TableProfile, "get_table_profile"
            )
        except Exception as e:
            results["get_table_profile"] = f"[FAIL] get_table_profile — {str(e)}"

    finally:
        # ── Step 9: destroy_sandbox ──────────────
        # This ALWAYS runs — even if something above crashed
        if sandbox_id:
            try:
                adapter.destroy_sandbox(sandbox_id)
                results["destroy_sandbox"] = "[PASS] destroy_sandbox"
            except Exception as e:
                results["destroy_sandbox"] = (
                    f"[FAIL] destroy_sandbox — {str(e)}"
                )
        else:
            results["destroy_sandbox"] = (
                "[SKIP] destroy_sandbox — sandbox was never created"
            )

    # ── Print results ────────────────────────────
    for method, result in results.items():
        print(result)

    passed = sum(1 for r in results.values() if r.startswith("[PASS]"))
    total = len(results)

    print("=" * 45)
    print(f"Result: {passed}/{total} PASSED")
    if passed == total:
        print("✅ All checks passed")
    else:
        print("❌ Some checks failed — review output above")

    return results


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="QLift Target Adapter Compliance Harness"
    )
    parser.add_argument(
        "--adapter",
        required=True,
        help="adapter name e.g. bigquery"
    )
    parser.add_argument(
        "--project",
        required=False,
        default="my-gcp-project",
        help="GCP project id for connection config"
    )
    args = parser.parse_args()

    # Dynamically load the adapter class
    # e.g. --adapter bigquery loads BigQueryAdapter
    adapter_map = {
        "bigquery": "qlift.target.ta02.bigquery.adapter.BigQueryAdapter",
    }

    if args.adapter not in adapter_map:
        print(f"Unknown adapter: {args.adapter}")
        print(f"Available: {list(adapter_map.keys())}")
        return

    module_path, class_name = adapter_map[args.adapter].rsplit(".", 1)
    module = importlib.import_module(module_path)
    AdapterClass = getattr(module, class_name)

    adapter = AdapterClass()
    config = {"project_id": args.project}

    run_harness(adapter, config)


if __name__ == "__main__":
    main()
