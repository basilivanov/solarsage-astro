SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: install run migrate revise systemd

install:
	python3.12 -m venv .venv
	$(PIP) install -U pip wheel
	$(PIP) install -e ".[dev]"

run:
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

migrate:
	.venv/bin/alembic upgrade head

revise:
	.venv/bin/alembic revision --autogenerate -m "$(m)"

systemd:
	sudo cp ../../infra/systemd/astro-api.service /etc/systemd/system/
	sudo cp ../../infra/systemd/astro-worker.service /etc/systemd/system/
	sudo systemctl daemon-reload
