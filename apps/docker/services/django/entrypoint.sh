#!/bin/bash
set -e

# Ожидаем доступности PostgreSQL
echo "Ожидание PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL доступен"

# Ожидаем доступности Redis
echo "Ожидание Redis..."
while ! nc -z redis 6379; do
  sleep 0.5
done
echo "Redis доступен"

# Применяем миграции
echo "Применение миграций..."
python manage.py migrate --noinput

# Собираем статику
echo "Сбор статики..."
python manage.py collectstatic --noinput --clear

# Создаем суперпользователя если нужно
if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Создание суперпользователя..."
    python manage.py createsuperuser --noinput || true
fi

# Запускаем сервер
exec "$@"
