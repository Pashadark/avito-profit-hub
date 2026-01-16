#!/bin/bash
# Упрощенный entrypoint для Windows Docker

echo "Запуск Django приложения..."

# Применяем миграции
python manage.py migrate --noinput

# Собираем статику
python manage.py collectstatic --noinput --clear

# Запускаем сервер
exec "$@"
