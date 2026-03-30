PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

.PHONY: api-venv api-test web-install web-test test

api-venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install pytest

api-test:
	cd apps/api && ../../$(PYTEST) tests/test_smoke.py -v

web-install:
	cd apps/web && pnpm install

web-test:
	cd apps/web && pnpm test -- --run

test: api-test web-test
