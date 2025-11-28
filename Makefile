PYTHON ?= python
MANAGE := vacation_workflow/manage.py
URL ?= localhost:8000
APP_URL ?= http://localhost:8000/static/index.html
FRONTEND_DIR := frontend
STATIC_DIST := vacation_workflow/static/dist
IMAGE ?= d0mhate/vacation-workflow
CONTAINER ?= vacation-workflow
DATE_TAG := $(shell date +%Y-%m-%d)
IMAGE_DATED := $(IMAGE):$(DATE_TAG)

.PHONY: help install migrate superuser demo-users run setup start db stop logs notifications reset-db flush reset-demo 

help:
	@echo "Available targets:"
	@echo "  install         - установить Python-зависимости (requirements.txt)"
	@echo "  migrate         - применить миграции"
	@echo "  superuser       - создать суперпользователя Django"
	@echo "  demo-users      - создать демо-учётки (employee/manager/hr)"
	@echo "  run             - запустить Django dev-сервер"
	@echo "  setup           - install + migrate + demo-users"
	@echo "  start           - setup и старт dev-сервера"
	@echo "  db              - подключиться к sqlite (dbshell)"
	@echo "  notifications   - сгенерировать уведомления (команда Django)"
	@echo "  fe-install      - npm install (frontend)"
	@echo "  fe-build        - собрать Vite в static/dist"
	@echo "  fe-dev          - запустить Vite dev server"
	@echo "  fe-clean        - удалить dist/node_modules фронта"
	@echo "  docker-build    - собрать Docker-образ"
	@echo "  docker-build-dated - собрать образ с датой (TAG=$(DATE_TAG))"
	@echo "  docker-run      - запустить контейнер (порт 8000)"
	@echo "  docker-push     - отправить образ ($(IMAGE)) в реестр"
	@echo "  docker-push-dated - отправить образ с датой ($(IMAGE_DATED))"
	@echo "  docker-stop     - остановить контейнер"
	@echo "  docker-logs     - логи контейнера"
	@echo "  compose-up      - docker-compose up (build + run)"
	@echo "  compose-down    - docker-compose down"
	@echo "  compose-logs    - docker-compose logs -f"
	@echo "  compose-dev-up  - compose в dev-режиме с volume (код монтируется)"
	@echo "  compose-dev-down- остановить dev-compose"
	@echo "  compose-dev-logs- логи dev-compose"
	@echo "  up              - алиас compose-up с подсказками и открытием URL"
	@echo "  pretty-up       - анимированный запуск (build + up)"
	@echo "  down            - алиас compose-down"
	@echo "  open-url        - открыть браузер на $(APP_URL)"
	@echo "  demo-tips       - подсказки по демо-командам"

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

docker-build:
	docker build -t $(IMAGE) .

docker-build-dated:
	docker build -t $(IMAGE_DATED) .
	@echo "Built $(IMAGE_DATED). Если нужен latest: docker tag $(IMAGE_DATED) $(IMAGE)"

docker-push:
	docker push $(IMAGE)

docker-push-dated:
	docker push $(IMAGE_DATED)

docker-run:
	docker run --rm -d --name $(CONTAINER) -p 8000:8000 $(IMAGE)

docker-stop:
	-docker stop $(CONTAINER)

docker-logs:
	docker logs -f $(CONTAINER)

compose-up:
	docker-compose up --build -d

compose-down:
	docker-compose down

compose-logs:
	docker-compose logs -f

compose-dev-up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

compose-dev-down:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

compose-dev-logs:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Aliases
up: pretty-up demo-tips open-url

down: compose-down

open-url:
	@echo "Открываю $(APP_URL)..."
	@ (command -v xdg-open >/dev/null 2>&1 && xdg-open "$(APP_URL)") || \
	  (command -v open >/dev/null 2>&1 && open "$(APP_URL)") || \
	  (command -v start >/dev/null 2>&1 && start "$(APP_URL)") || \
	  echo "Откройте вручную: $(APP_URL)"

demo-tips:
	@echo "Полезные команды для демо:"
	@echo "  make demo-users       # создать/обновить демо-учётки (employee/manager/hr)"
	@echo "  make notifications    # сгенерировать уведомления"
	@echo "  make logs             # посмотреть логи Django (tail)"

# Немного «анимации» в терминале
pretty-up:
	@printf "🚀 Старт запуска окружения\n"
	@printf "🔧 Шаг 1/2: сборка образа...\n"
	@docker-compose build
	@printf "⚙️  Шаг 2/2: поднимаю сервисы...\n"
	@docker-compose up -d
	@printf "Готово. Откройте: $(APP_URL)\n"
