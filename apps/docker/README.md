# Docker для Avito Profit Hub


## Структура


```
apps/docker/
├── docker-compose.yml          # Основная конфигурация
├── docker-compose.override.yml # Для разработки
├── docker-compose.prod.yml     # Продакшен
├── docker-compose.test.yml     # Тестирование
├── docker-compose.local.yml    # Локальная (Windows)
├── .env.example               # Пример переменных
├── Makefile                   # Команды
├── README.md                  # Эта документация
│
├── services/                  # Dockerfile для сервисов
│   ├── django/
│   ├── bot/
│   ├── celery/
│   ├── redis/
│   └── postgres/
│
└── nginx/                     # Конфигурация nginx
    ├── nginx.conf
    ├── ssl/
    └── sites-available/
```


## Быстрый старт


1. **Настройка окружения:**
```bash
cd apps/docker
cp .env.example .env
# Отредактируй .env файл
```


2. **Запуск для разработки:**
```bash
make build
make up
```


3. **Проверка:**
```bash
docker-compose logs -f
docker-compose ps
docker-compose exec django bash
```


## Полезные команды


### С Makefile:
```bash
make build      # Собрать образы
make up         # Запустить
make down       # Остановить
make logs       # Показать логи
make migrate    # Применить миграции
make superuser  # Создать суперпользователя
make shell      # Зайти в контейнер Django
make clean      # Очистить всё
```


### Без Makefile:
```bash
docker-compose up -d
docker-compose logs -f django
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser
docker-compose exec django python manage.py collectstatic
docker-compose down
docker-compose down -v
```


## Для Windows


Используй `docker-compose.local.yml` для Windows специфичных настроек.


## Продакшен


```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```


## Устранение проблем


1. **Permission denied на entrypoint.sh:**
```bash
chmod +x apps/docker/services/django/entrypoint.sh
```


2. **PostgreSQL не запускается:**
```bash
docker-compose logs postgres
docker-compose down -v
```


3. **Django не видит PostgreSQL:**
```bash
docker-compose exec django python -c "import psycopg2; psycopg2.connect(host='postgres', dbname='avito_profit_hub', user='avito_user', password='your_password')"
```
