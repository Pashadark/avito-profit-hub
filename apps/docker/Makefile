# Makefile для управления Docker

.PHONY: help build up down logs restart clean migrate superuser shell django bot celery

help:
	@echo "Доступные команды:"
	@echo "  make build      - Собрать образы"
	@echo "  make up         - Запустить контейнеры"
	@echo "  make down       - Остановить контейнеры"
	@echo "  make logs       - Показать логи"
	@echo "  make restart    - Перезапустить контейнеры"
	@echo "  make clean      - Очистить контейнеры и volumes"
	@echo "  make migrate    - Применить миграции"
	@echo "  make superuser  - Создать суперпользователя"
	@echo "  make shell      - Зайти в контейнер Django"
	@echo "  make django     - Логи Django"
	@echo "  make bot        - Логи бота"
	@echo "  make celery     - Логи Celery"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

clean:
	docker-compose down -v
	docker system prune -f

migrate:
	docker-compose exec django python manage.py migrate

superuser:
	docker-compose exec django python manage.py createsuperuser

shell:
	docker-compose exec django bash

django:
	docker-compose logs -f django

bot:
	docker-compose logs -f bot

celery:
	docker-compose logs -f celery celery-beat

# Для разработки
dev:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Для продакшена
prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
