SHELL := /bin/bash

SOLARSAGE_GIT ?= git@github.com:<you>/solarsage.git
SOLARSAGE_DIR ?= /opt/solarsage

.PHONY: install run systemd

install:
	sudo mkdir -p $(SOLARSAGE_DIR)
	sudo chown $$(id -u):$$(id -g) $(SOLARSAGE_DIR)
	if [ ! -d $(SOLARSAGE_DIR)/.git ]; then \
	  git clone $(SOLARSAGE_GIT) $(SOLARSAGE_DIR); \
	fi
	cd $(SOLARSAGE_DIR) && python3.12 -m venv .venv && \
	  .venv/bin/pip install -U pip wheel && \
	  .venv/bin/pip install -e . || true
	if [ -d $(SOLARSAGE_DIR)/third_party/swisseph ]; then \
	  cd $(SOLARSAGE_DIR)/third_party/swisseph && make libswe.a; \
	fi

run:
	cd $(SOLARSAGE_DIR) && .venv/bin/python -m solarsage.server --host 127.0.0.1 --port 18091

systemd:
	sudo cp ../../infra/systemd/solarsage.service /etc/systemd/system/
	sudo systemctl daemon-reload
