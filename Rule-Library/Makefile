.PHONY: install test test-acceptance test-coverage lint clean

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-acceptance:
	pytest tests/test_acceptance_criteria.py -v

test-coverage:
	pytest tests/test_all_rules_coverage.py -v

lint:
	python -m py_compile tests/conftest.py
	python -m py_compile tests/test_rule_schema.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
