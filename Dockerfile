FROM node:18-alpine AS frontend-builder
WORKDIR /app
# Ставим только package* для кэша зависимостей
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci
# Копируем остальное и собираем Vite
COPY frontend ./frontend
COPY vacation_workflow/static ./vacation_workflow/static
RUN cd frontend && npm run build


FROM python:3.12-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Системные зависимости (минимальный набор для pip)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY vacation_workflow ./vacation_workflow
# Собранный фронт из предыдущего этапа
COPY --from=frontend-builder /app/vacation_workflow/static/dist ./vacation_workflow/static/dist
# Точка входа
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
CMD ["./docker-entrypoint.sh"]
