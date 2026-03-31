PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
DEMO_DATABASE_URL ?= sqlite+pysqlite:////tmp/swinginsight-demo.db

.PHONY: api-venv api-test web-install web-test demo test

api-venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -e apps/api pytest

api-test:
	cd apps/api && ../../$(PYTEST) -v

web-install:
	cd apps/web && pnpm install

web-test:
	cd apps/web && pnpm test -- --run

demo:
	DATABASE_URL=$(DEMO_DATABASE_URL) ./scripts/run_demo.sh

test: api-test web-test
