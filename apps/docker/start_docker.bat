@echo off
REM Скрипт запуска Docker для Windows

echo ========================================
echo ЗАПУСК AVITO PROFIT HUB В DOCKER
echo ========================================

REM Переходим в папку с docker-compose
cd /d %~dp0

REM Проверяем наличие .env файла
if not exist .env (
    echo Файл .env не найден!
    echo Создаю из примера...
    copy .env.example .env
    echo Пожалуйста, отредактируй .env файл
    pause
    exit /b 1
)

REM Собираем образы
echo Сборка Docker образов...
docker-compose build --no-cache

REM Запускаем контейнеры
echo Запуск контейнеров...
docker-compose up -d

echo ========================================
echo ГОТОВО!
echo ========================================
echo
echo Сервисы:
echo - Django:     http://localhost:8000
echo - PostgreSQL: localhost:5432
echo - Redis:      localhost:6379
echo - pgAdmin:    http://localhost:5050
echo
echo Команды:
echo - Логи:       docker-compose logs -f
echo - Остановка:  docker-compose down
echo - Перезапуск: docker-compose restart
echo
pause
