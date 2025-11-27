PYTHON ?= python
MANAGE := vacation_workflow/manage.py
URL ?= localhost:8000
FRONTEND_DIR := frontend
STATIC_DIST := vacation_workflow/static/dist

.PHONY: help install migrate superuser demo-users run setup start db stop logs notifications reset-db flush reset-demo 

help:
	@echo "Available targets:"
	@echo "  install         - install Python dependencies from requirements.txt"
	@echo "  migrate         - apply database migrations"
	@echo "  superuser       - create a Django superuser (interactive)"
	@echo "  demo-users      - create demo employee/manager/hr users with default passwords"
	@echo "  run             - start the Django development server"
	@echo "  setup           - install deps, migrate, seed demo users"
	@echo "  start           - setup backend and start dev server"
	@echo "  db              - connect to sqlite db"
	@echo "  notifications   - generate vacation reminder notifications (management command)"
	@echo "  fe-install      - npm install (frontend)"
	@echo "  fe-build        - build Vite bundle to static/dist"
	@echo "  fe-dev          - run Vite dev server"
	@echo "  fe-clean        - remove built dist"

install:
	$(PYTHON) -m pip install -r requirements.txt

migrate:
	$(PYTHON) $(MANAGE) migrate

superuser:
	$(PYTHON) $(MANAGE) createsuperuser

demo-users:
	$(PYTHON) $(MANAGE) seed_demo_users

run:
	@echo "Starting Django..."
	$(PYTHON) $(MANAGE) runserver $(URL)

logs:
	@tail -f /tmp/django.log

db:
	$(PYTHON) $(MANAGE) dbshell

setup: install migrate demo-users

start: setup run

notifications:
	$(PYTHON) $(MANAGE) generate_vacation_notifications

reset-db:
	rm -f vacation_workflow/db.sqlite3
	find vacation_workflow/vacation_app/migrations -type f ! -name "__init__.py" -delete
	$(PYTHON) $(MANAGE) makemigrations
	$(PYTHON) $(MANAGE) migrate

flush:
	$(PYTHON) $(MANAGE) flush --noinput

reset-demo:
	rm -f vacation_workflow/db.sqlite3
	find vacation_workflow/vacation_app/migrations -type f ! -name "__init__.py" -delete
	$(PYTHON) $(MANAGE) makemigrations
	$(PYTHON) $(MANAGE) migrate
	$(PYTHON) $(MANAGE) seed_demo_users

# Frontend helpers
fe-install:
	cd $(FRONTEND_DIR) && npm install

fe-build:
	cd $(FRONTEND_DIR) && npm run build

fe-dev:
	cd $(FRONTEND_DIR) && npm run dev -- --host

fe-clean:
	rm -rf $(STATIC_DIST) $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/node_modules
