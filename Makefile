PYTHON ?= python
MANAGE := vacation_workflow/manage.py

.PHONY: help install migrate superuser demo-users run setup start db

help:
	@echo "Available targets:"
	@echo "  install    - install Python dependencies from requirements.txt"
	@echo "  migrate    - apply database migrations"
	@echo "  superuser  - create a Django superuser (interactive)"
	@echo "  demo-users - create demo employee/manager/hr users with default passwords"
	@echo "  run        - start the Django development server"
	@echo "  setup      - install dependencies and run migrations"
	@echo "  start      - setup and start the development server"
	@echo "  db      	- connect to sqlite db"

install:
	$(PYTHON) -m pip install -r requirements.txt

migrate:
	$(PYTHON) $(MANAGE) migrate

superuser:
	$(PYTHON) $(MANAGE) createsuperuser

demo-users:
	$(PYTHON) $(MANAGE) seed_demo_users

run:
	$(PYTHON) $(MANAGE) runserver 127.0.0.1:8000

db:
	$(PYTHON) $(MANAGE) dbshell

setup: install migrate

start: setup run
