#!/usr/bin/env python3
"""
🎯 КОМПЛЕКСНАЯ ПРОВЕРКА ПАРСЕРА AVITO-PROFIT-HUB
Проверяет ВСЕ компоненты системы перед запуском.
Паштет, если что-то сломано - фиксим сразу!
"""

import sys
import os
import json
import pickle
import joblib
import numpy as np
from datetime import datetime
import importlib
import traceback

# Добавляем путь к проекту
sys.path.append('.')
sys.path.append('apps')

# Конфигурация проверок
CHECKS = {
    'ml_models': True,  # ML модели
    'django_models': True,  # Django модели
    'database': True,  # База данных
    'browser': True,  # Браузер (Selenium)
    'ai_components': True,  # AI компоненты
    'configs': True,  # Конфигурации
    'full_test': True  # Полный тест парсера
}

print("=" * 70)
print("🔥 КОМПЛЕКСНАЯ ПРОВЕРКА AVITO-PROFIT-HUB")
print("=" * 70)
print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Директория: {os.getcwd()}")
print(f"Python: {sys.version}")
print("=" * 70)


def check_ml_models():
    """Проверка ML моделей"""
    print("\n🎯 1. ПРОВЕРКА ML МОДЕЛЕЙ")
    print("-" * 50)

    results = {
        'freshness_model': False,
        'price_model': False,
        'scalers': False
    }

    # 1. Модель свежести
    try:
        if os.path.exists('freshness_model.joblib'):
            print("🔍 Проверяем модель свежести...")
            data = joblib.load('freshness_model.joblib')

            model = data.get('model')
            scaler = data.get('scaler')

            if model:
                print(f"   ✅ Модель: {type(model).__name__}")

                # Проверяем что можно сделать предсказание
                if hasattr(model, 'predict'):
                    # Тестовое предсказание
                    X_test = np.random.rand(1, 10)
                    if scaler and hasattr(scaler, 'transform'):
                        X_test = scaler.transform(X_test)

                    prediction = model.predict(X_test)
                    print(f"   ✅ Предсказание работает: {prediction[0]:.4f}")
                    results['freshness_model'] = True
                else:
                    print("   ❌ Модель не имеет метода predict")
            else:
                print("   ❌ Модель не найдена в файле")

            # Проверка scaler
            if scaler:
                print(f"   ✅ Scaler: {type(scaler).__name__}")
                if hasattr(scaler, 'mean_'):
                    print(f"   ✅ Scaler обучен ({len(scaler.mean_)} фичей)")
                    results['scalers'] = True
                else:
                    print("   ⚠️ Scaler не обучен")
            else:
                print("   ❌ Scaler не найден")
        else:
            print("   ❌ Файл freshness_model.joblib не найден")

    except Exception as e:
        print(f"   ❌ Ошибка проверки модели свежести: {e}")
        traceback.print_exc()

    # 2. Модель цены
    try:
        price_files = ['super_price_model.joblib', 'ultra_price_model.joblib']
        found = False

        for price_file in price_files:
            if os.path.exists(price_file):
                print(f"\n🔍 Проверяем модель цены ({price_file})...")
                data = joblib.load(price_file)

                model = data.get('model')
                scaler = data.get('scaler')

                if model and hasattr(model, 'predict'):
                    print(f"   ✅ Модель цены: {type(model).__name__}")

                    # Тестовое предсказание
                    X_test = np.random.rand(1, 5)
                    if scaler and hasattr(scaler, 'transform'):
                        X_test = scaler.transform(X_test)

                    prediction = model.predict(X_test)
                    print(f"   ✅ Предсказание цены: {prediction[0]:.2f} руб")
                    results['price_model'] = True
                    found = True
                    break
                else:
                    print(f"   ❌ Модель в {price_file} некорректна")

        if not found:
            print("   ❌ Ни одна модель цены не найдена или не работает")

    except Exception as e:
        print(f"   ❌ Ошибка проверки модели цены: {e}")

    return results


def check_django_models():
    """Проверка Django моделей"""
    print("\n🎯 2. ПРОВЕРКА DJANGO МОДЕЛЕЙ")
    print("-" * 50)

    results = {
        'models_loaded': False,
        'database_connection': False,
        'migrations': False
    }

    try:
        # Пытаемся загрузить Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avito_profit_hub.settings')

        import django
        django.setup()

        print("✅ Django успешно инициализирован")
        results['models_loaded'] = True

        # Проверяем основные модели
        from django.apps import apps

        required_models = [
            'bot.Product',
            'bot.UserProfile',
            'bot.Notification',
            'parsing.ParserSession'
        ]

        for model_name in required_models:
            try:
                model = apps.get_model(model_name)
                print(f"   ✅ Модель {model_name} загружена")
            except Exception as e:
                print(f"   ❌ Ошибка загрузки модели {model_name}: {e}")

        # Проверяем соединение с БД
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("   ✅ Соединение с БД работает")
            results['database_connection'] = True

        # Проверяем миграции
        from django.core.management import execute_from_command_line
        try:
            execute_from_command_line(['manage.py', 'makemigrations', '--check', '--dry-run'])
            print("   ✅ Миграции актуальны")
            results['migrations'] = True
        except SystemExit:
            print("   ⚠️ Требуются миграции")

    except Exception as e:
        print(f"❌ Ошибка проверки Django: {e}")
        traceback.print_exc()

    return results


def check_ai_components():
    """Проверка AI компонентов"""
    print("\n🎯 3. ПРОВЕРКА AI КОМПОНЕНТОВ")
    print("-" * 50)

    results = {
        'freshness_predictor': False,
        'price_predictor': False,
        'query_optimizer': False,
        'learning_system': False
    }

    ai_modules = [
        ('apps.parsing.ai.ml_freshness_predictor', 'ML свежесть'),
        ('apps.parsing.ai.ml_price_predictor', 'ML цена'),
        ('apps.parsing.ai.query_optimizer', 'Оптимизатор запросов'),
        ('apps.parsing.ai.learning_system', 'Система обучения')
    ]

    for module_name, description in ai_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"✅ {description} загружен")

            if 'freshness' in module_name:
                results['freshness_predictor'] = True
            elif 'price' in module_name:
                results['price_predictor'] = True
            elif 'query' in module_name:
                results['query_optimizer'] = True
            elif 'learning' in module_name:
                results['learning_system'] = True

        except Exception as e:
            print(f"❌ Ошибка загрузки {description}: {e}")

    return results


def check_browser_setup():
    """Проверка настройки браузера"""
    print("\n🎯 4. ПРОВЕРКА БРАУЗЕРА И SELENIUM")
    print("-" * 50)

    results = {
        'selenium': False,
        'webdriver': False,
        'user_agents': False
    }

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        print("✅ Selenium установлен")
        results['selenium'] = True

        # Проверяем наличие ChromeDriver
        try:
            # Сначала пробуем найти в PATH
            from webdriver_manager.chrome import ChromeDriverManager
            print("✅ ChromeDriverManager доступен")
            results['webdriver'] = True
        except ImportError:
            print("⚠️ webdriver-manager не установлен")

        # Проверяем user agents
        ua_file = 'apps/parsing/user_agents.json'
        if os.path.exists(ua_file):
            with open(ua_file, 'r', encoding='utf-8') as f:
                user_agents = json.load(f)
                print(f"✅ User Agents загружены: {len(user_agents)} штук")
                results['user_agents'] = True
        else:
            print("⚠️ Файл user_agents.json не найден")

    except Exception as e:
        print(f"❌ Ошибка проверки Selenium: {e}")

    return results


def check_configs():
    """Проверка конфигураций"""
    print("\n🎯 5. ПРОВЕРКА КОНФИГУРАЦИЙ")
    print("-" * 50)

    results = {
        'settings': False,
        'env': False,
        'parser_config': False
    }

    # Проверяем settings.py
    try:
        from avito_profit_hub import settings
        print("✅ settings.py загружен")

        # Проверяем ключевые настройки
        required_settings = ['DEBUG', 'DATABASES', 'SECRET_KEY', 'ALLOWED_HOSTS']
        for setting in required_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)
                if setting == 'SECRET_KEY' and value:
                    print(f"   ✅ {setting}: {'установлен' if value else 'отсутствует'}")
                else:
                    print(f"   ✅ {setting}: {value}")
            else:
                print(f"   ⚠️ {setting}: не найден")

        results['settings'] = True

    except Exception as e:
        print(f"❌ Ошибка загрузки settings.py: {e}")

    # Проверяем .env файл
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"✅ Файл {env_file} найден")
        results['env'] = True
    else:
        print(f"⚠️ Файл {env_file} не найден")

    # Проверяем конфиг парсера
    parser_config = 'apps/parsing/config/parser_config.json'
    if os.path.exists(parser_config):
        with open(parser_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
            print(f"✅ Конфиг парсера загружен: {len(config)} параметров")
            results['parser_config'] = True
    else:
        print(f"⚠️ Конфиг парсера не найден: {parser_config}")

    return results


def run_test_parser():
    """Запуск тестового парсера"""
    print("\n🎯 6. ТЕСТОВЫЙ ЗАПУСК ПАРСЕРА")
    print("-" * 50)

    results = {
        'quick_test': False,
        'find_products': False,
        'validation': False,
        'save_to_db': False
    }

    try:
        # Импортируем минимальный набор для теста
        from apps.parsing.selenium_parser import SeleniumSuperParser
        from apps.parsing.validator import ProductValidator

        print("✅ Компоненты парсера загружены")

        # Создаем тестовый парсер (без реального браузера)
        parser = SeleniumSuperParser(window_count=0)  # 0 окон = тестовый режим

        if hasattr(parser, 'health_check'):
            health = parser.health_check()
            print(f"✅ Health check: {health}")
            results['quick_test'] = True

        # Тест валидатора
        validator = ProductValidator()
        test_product = {
            'title': 'iPhone 13 Pro 128GB Тестовый',
            'price': 45000,
            'url': 'https://www.avito.ru/test',
            'freshness_score': 0.8
        }

        is_valid, reason = validator.validate_product(test_product)
        print(f"✅ Тест валидатора: {'Пройден' if is_valid else 'Не пройден'} - {reason}")
        results['validation'] = True if is_valid else False

        # Проверяем возможность сохранения в БД
        try:
            from bot.models import Product
            print("✅ Модель Product доступна для сохранения")
            results['save_to_db'] = True
        except Exception as e:
            print(f"⚠️ Ошибка доступа к модели Product: {e}")

    except Exception as e:
        print(f"❌ Ошибка тестового запуска: {e}")
        traceback.print_exc()

    return results


def generate_report(all_results):
    """Генерация отчета"""
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 70)

    total_checks = 0
    passed_checks = 0
    critical_issues = []
    warnings = []

    # Анализируем результаты
    for check_name, results in all_results.items():
        print(f"\n🔍 {check_name.upper().replace('_', ' ')}:")

        if isinstance(results, dict):
            for sub_check, status in results.items():
                total_checks += 1
                icon = "✅" if status else "❌"
                print(f"   {icon} {sub_check}")

                if status:
                    passed_checks += 1
                else:
                    # Критические проверки
                    critical_checks = ['freshness_model', 'price_model', 'database_connection']
                    if sub_check in critical_checks:
                        critical_issues.append(f"{check_name}.{sub_check}")
                    else:
                        warnings.append(f"{check_name}.{sub_check}")

    # Статистика
    success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(f"\n📈 СТАТИСТИКА:")
    print(f"   Всего проверок: {total_checks}")
    print(f"   Пройдено: {passed_checks}")
    print(f"   Успешность: {success_rate:.1f}%")

    # Рекомендации
    if critical_issues:
        print(f"\n🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ ({len(critical_issues)}):")
        for issue in critical_issues:
            print(f"   • {issue}")

        print("\n🔧 РЕКОМЕНДАЦИИ:")
        if 'ml_models.freshness_model' in critical_issues:
            print("   • Запусти: python fix_freshness_scaler.py")
        if 'ml_models.price_model' in critical_issues:
            print("   • Запусти: python fix_price_model.py")
        if 'django_models.database_connection' in critical_issues:
            print("   • Проверь настройки БД в settings.py и .env")

    if warnings:
        print(f"\n⚠️ ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):")
        for warning in warnings[:5]:  # Показываем первые 5
            print(f"   • {warning}")

    # Финальная оценка
    print("\n" + "=" * 70)
    if success_rate >= 90:
        print("🎉 СИСТЕМА ГОТОВА К РАБОТЕ! Запускай парсер!")
        print("   Команда: python run.py (вариант 1 или 4)")
    elif success_rate >= 70:
        print("⚠️ СИСТЕМА ТРЕБУЕТ ДОРАБОТОК, но может работать")
        print("   Исправь критические проблемы и запускай")
    else:
        print("❌ СИСТЕМА НЕ ГОТОВА. Нужны серьезные исправления.")

    print("=" * 70)

    return success_rate >= 70  # Система готова если успешность >= 70%


def backup_and_push():
    """Создание бекапа и пуша в git"""
    print("\n" + "=" * 70)
    print("💾 СОЗДАНИЕ БЕКАПА И PUSH В GIT")
    print("=" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_{timestamp}"

    try:
        # Создаем директорию для бекапа
        os.makedirs(backup_dir, exist_ok=True)

        # Копируем ключевые файлы
        important_files = [
            'freshness_model.joblib',
            'super_price_model.joblib',
            'ultra_price_model.joblib',
            'fixed_voting_regressor.py',
            'check_parser_system.py'
        ]

        print("📦 Копируем ключевые файлы:")
        for file in important_files:
            if os.path.exists(file):
                import shutil
                shutil.copy2(file, os.path.join(backup_dir, file))
                print(f"   ✅ {file}")

        print(f"\n💾 Бекап создан в: {backup_dir}")

        # Git commit и push
        print("\n🔀 Git операции:")

        # Проверяем статус git
        git_status = os.popen('git status --porcelain').read().strip()
        if git_status:
            print("   📝 Изменения обнаружены:")
            for line in git_status.split('\n'):
                if line:
                    print(f"     {line}")

            # Коммит
            commit_message = f"fix: проверка и фикс системы парсера {timestamp}"
            os.system(f'git add .')
            os.system(f'git commit -m "{commit_message}"')
            print(f"   ✅ Коммит: {commit_message}")

            # Push
            print("   🔼 Push в репозиторий...")
            os.system('git push origin main')
            print("   ✅ Изменения отправлены на GitHub")
        else:
            print("   📭 Нет изменений для коммита")

    except Exception as e:
        print(f"❌ Ошибка при создании бекапа: {e}")


def main():
    """Основная функция проверки"""

    all_results = {}

    # Выполняем проверки
    if CHECKS['ml_models']:
        all_results['ml_models'] = check_ml_models()

    if CHECKS['django_models']:
        all_results['django_models'] = check_django_models()

    if CHECKS['ai_components']:
        all_results['ai_components'] = check_ai_components()

    if CHECKS['browser']:
        all_results['browser'] = check_browser_setup()

    if CHECKS['configs']:
        all_results['configs'] = check_configs()

    if CHECKS['full_test']:
        all_results['full_test'] = run_test_parser()

    # Генерируем отчет
    system_ready = generate_report(all_results)

    # Если система готова - предлагаем создать бекап
    if system_ready:
        print("\n🍻 Паштет, система проверена! Хочешь создать бекап и запушить в git? (y/n)")
        choice = input(">>> ").strip().lower()

        if choice == 'y':
            backup_and_push()
            print("\n🎉 ВСЁ ГОТОВО! Запускай парсер командой:")
            print("   (.venv) PS C:\\Users\\pasahdark\\PycharmProjects\\avito_profit_hub> python run.py")
        else:
            print("\n👌 Ок, бекап пропускаем. Запускай парсер когда будешь готов!")
    else:
        print("\n🔧 Сначала исправь критические проблемы, потом запускай проверку снова.")


if __name__ == "__main__":
    main()