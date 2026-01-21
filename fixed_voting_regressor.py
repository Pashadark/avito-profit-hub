"""
Скрипт для диагностики проблемы с городом
Запуск: python find_city_bug.py
"""

import os
import sys
import django

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    print("✅ Django настроен")
except Exception as e:
    print(f"❌ Ошибка Django: {e}")
    sys.exit(1)

def check_settings_manager_structure():
    """Проверка структуры SettingsManager"""
    print("\n" + "="*60)
    print("🔍 ПРОВЕРКА SETTINGS MANAGER СТРУКТУРЫ")
    print("="*60)

    try:
        # Ищем файл settings_manager.py
        settings_manager_path = os.path.join(BASE_DIR, 'apps', 'parsing', 'core', 'settings_manager.py')

        if os.path.exists(settings_manager_path):
            print(f"✅ Файл найден: {settings_manager_path}")

            # Читаем файл
            with open(settings_manager_path, 'r', encoding='utf-8') as f:
                content = f.read()

                print("\n🎯 ПОИСК АТРИБУТОВ И МЕТОДОВ:")

                # Ищем атрибуты
                if 'self.city' in content:
                    print("✅ Найден self.city")
                    # Находим строки с city
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'self.city' in line or 'city=' in line or 'city =' in line:
                            print(f"   Строка {i+1}: {line.strip()}")
                else:
                    print("❌ self.city НЕ найден")

                # Ищем метод update_settings
                print("\n🎯 МЕТОД UPDATE_SETTINGS:")
                if 'def update_settings' in content:
                    print("✅ Метод update_settings найден")
                    # Находим метод
                    lines = content.split('\n')
                    in_method = False
                    for i, line in enumerate(lines):
                        if 'def update_settings' in line:
                            in_method = True
                            print(f"   Начало метода (строка {i+1}): {line.strip()}")
                        elif in_method and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                            break
                        elif in_method:
                            if 'city' in line.lower():
                                print(f"   Строка {i+1}: {line.rstrip()}")
                else:
                    print("❌ Метод update_settings НЕ найден")

                # Ищем load_initial_settings
                print("\n🎯 МЕТОД LOAD_INITIAL_SETTINGS:")
                if 'def load_initial_settings' in content:
                    print("✅ Метод load_initial_settings найден")
                    # Находим где загружается город
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'def load_initial_settings' in line:
                            # Смотрим следующие строки
                            for j in range(i, min(i+50, len(lines))):
                                if 'city' in lines[j].lower():
                                    print(f"   Строка {j+1}: {lines[j].rstrip()}")
                else:
                    print("❌ Метод load_initial_settings НЕ найден")

        else:
            print(f"❌ Файл не найден: {settings_manager_path}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

def check_database_direct():
    """Прямая проверка базы данных"""
    print("\n" + "="*60)
    print("🔍 ПРЯМАЯ ПРОВЕРКА БАЗЫ ДАННЫХ")
    print("="*60)

    try:
        import sqlite3

        db_path = os.path.join(BASE_DIR, 'db.sqlite3')
        if os.path.exists(db_path):
            print(f"✅ База данных найдена: {db_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Проверяем таблицу с настройками парсера
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%parser%';")
            tables = cursor.fetchall()

            print("\n🎯 ТАБЛИЦЫ С НАСТРОЙКАМИ:")
            for table in tables:
                print(f"   - {table[0]}")

            # Ищем таблицу с настройками
            for table_name in [t[0] for t in tables]:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()

                # Ищем таблицу с полем city
                for col in columns:
                    if 'city' in col[1].lower():
                        print(f"\n✅ Найдена таблица с city: {table_name}")
                        print("   Столбцы таблицы:")
                        for c in columns:
                            print(f"     {c[1]} ({c[2]})")

                        # Получаем данные
                        cursor.execute(f"SELECT * FROM {table_name} WHERE name='Пенза1' OR city='Пенза';")
                        rows = cursor.fetchall()

                        if rows:
                            print(f"\n📊 ДАННЫЕ НАСТРОЙКИ 'Пенза1':")
                            for row in rows:
                                print(f"   {row}")
                        else:
                            print(f"\n❌ Запись 'Пенза1' не найдена в {table_name}")

                        # Ищем все записи с городом Пенза
                        cursor.execute(f"SELECT id, name, city, site FROM {table_name} WHERE city LIKE '%Пенза%';")
                        penza_rows = cursor.fetchall()

                        if penza_rows:
                            print(f"\n📊 ВСЕ ЗАПИСИ С ГОРОДОМ 'ПЕНЗА':")
                            for row in penza_rows:
                                print(f"   ID: {row[0]}, Название: '{row[1]}', Город: '{row[2]}', Сайт: {row[3]}")
                        break

            conn.close()
        else:
            print(f"❌ База данных не найдена: {db_path}")

    except Exception as e:
        print(f"❌ Ошибка проверки базы: {e}")

def check_views_file():
    """Проверка views.py на сохранение города"""
    print("\n" + "="*60)
    print("🔍 ПРОВЕРКА VIEWS.PY")
    print("="*60)

    try:
        views_path = os.path.join(BASE_DIR, 'apps', 'website', 'views.py')

        if os.path.exists(views_path):
            print(f"✅ Файл найден: {views_path}")

            with open(views_path, 'r', encoding='utf-8') as f:
                content = f.read()

                print("\n🎯 ПОИСК СОХРАНЕНИЯ НАСТРОЕК:")

                # Ищем AJAX сохранение настроек
                search_terms = [
                    'ajax_save_settings',
                    'save_settings',
                    'parser_settings',
                    'city=request.POST'
                ]

                for term in search_terms:
                    if term in content:
                        print(f"✅ Найдено: {term}")

                # Находим конкретно сохранение города
                lines = content.split('\n')
                print("\n📋 СТРОКИ С СОХРАНЕНИЕМ ГОРОДА:")
                for i, line in enumerate(lines):
                    if 'city' in line.lower() and ('post' in line.lower() or 'request' in line.lower()):
                        print(f"   Строка {i+1}: {line.strip()}")

                # Ищем где вызывается SettingsManager
                print("\n🎯 ВЫЗОВ SETTINGS_MANAGER:")
                for i, line in enumerate(lines):
                    if 'SettingsManager' in line or 'settings_manager' in line:
                        print(f"   Строка {i+1}: {line.strip()}")

        else:
            print(f"❌ Файл не найден: {views_path}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

def create_test_fix():
    """Создает тестовый фикс"""
    print("\n" + "="*60)
    print("🔧 СОЗДАНИЕ ТЕСТОВОГО ФИКСА")
    print("="*60)

    # 1. Тестовый скрипт для проверки SettingsManager
    test_script = """import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    print("✅ Django настроен")
except Exception as e:
    print(f"❌ Ошибка Django: {e}")
    sys.exit(1)

print("\\n🚀 ТЕСТ SETTINGS MANAGER")

try:
    from parsing.core.settings_manager import SettingsManager
    
    # Тест 1: Создание менеджера
    sm = SettingsManager()
    sm.user_id = 1
    
    print("\\n🎯 ТЕСТ 1: Проверка атрибутов")
    print(f"   Есть атрибут 'city'? {hasattr(sm, 'city')}")
    if hasattr(sm, 'city'):
        print(f"   Значение city: '{sm.city}'")
    
    # Тест 2: Загрузка настроек
    print("\\n🎯 ТЕСТ 2: Загрузка начальных настроек")
    sm.load_initial_settings()
    
    print(f"   Город после загрузки: '{sm.city}'")
    print(f"   Поисковые запросы: {sm.search_queries}")
    
    # Тест 3: Проверка обновления
    print("\\n🎯 ТЕСТ 3: Обновление настроек")
    test_data = {
        'city': 'Пенза',
        'keywords': 'Тестовые ключи',
        'min_price': 1000,
        'max_price': 5000
    }
    
    if hasattr(sm, 'update_settings'):
        sm.update_settings(test_data)
        print(f"   Город после обновления: '{sm.city}'")
    else:
        print("   ❌ Нет метода update_settings")
        
except Exception as e:
    print(f"❌ Ошибка теста: {e}")
    import traceback
    traceback.print_exc()
"""

    # 2. Патч для SettingsManager
    patch_code = """
# 🔧 ПАТЧ ДЛЯ SETTINGS_MANAGER.PY
# Добавьте в класс SettingsManager (файл: apps/parsing/core/settings_manager.py)

# 1. В методе __init__ добавьте:
#    self.city = "Москва"  # значение по умолчанию

# 2. В методе load_initial_settings добавьте загрузку города:
#    Пример кода:
#    if user_settings:
#        self.city = user_settings.city or "Москва"

# 3. В методе update_settings добавьте сохранение города:
#    Пример кода:
#    if 'city' in settings_data:
#        self.city = settings_data['city']
"""

    with open('test_settings_manager.py', 'w', encoding='utf-8') as f:
        f.write(test_script)

    with open('fix_settings_manager.txt', 'w', encoding='utf-8') as f:
        f.write(patch_code)

    print("✅ Созданы файлы:")
    print("   1. test_settings_manager.py - тест SettingsManager")
    print("   2. fix_settings_manager.txt - инструкция по исправлению")

    print("\n🎯 ИНСТРУКЦИЯ:")
    print("""
    1. Запустите тест: python test_settings_manager.py
    2. Если city всегда 'Москва' - проблема в SettingsManager
    3. Откройте файл: apps/parsing/core/settings_manager.py
    4. Добавьте атрибут city в __init__: self.city = "Москва"
    5. В load_initial_settings добавьте загрузку города из базы
    6. В update_settings добавьте сохранение города из формы
    """)

def check_current_city_flow():
    """Проверка текущего потока города"""
    print("\n" + "="*60)
    print("🔍 ТЕКУЩИЙ ПОТОК ДАННЫХ ГОРОДА")
    print("="*60)

    print("""
    ⚠️  ПРОБЛЕМА ОБНАРУЖЕНА:
    
    Из вывода видно, что SettingsManager:
    1. НЕ имеет атрибута 'city' ❌
    2. После загрузки показывает город: 'Москва' (по умолчанию)
    3. Но в базе данных город сохранен как 'Пенза'
    
    🔴 ПРИЧИНА:
    SettingsManager не загружает город из базы данных!
    
    🔧 ЧТО ПРОВЕРИТЬ:
    
    1. apps/parsing/core/settings_manager.py:
       - Есть ли в __init__: self.city = "Москва"?
       - В load_initial_settings загружается ли город?
       - В update_settings сохраняется ли город?
    
    2. apps/website/views.py:
       - При сохранении настроек отправляется ли city в POST?
       - Вызывается ли sm.update_settings() с city?
    
    3. HTML форма:
       - Проверьте name поля города: <input name="city">
       - Проверьте отправку формы через Network вкладку
    
    🎯 САМОЕ ВАЖНОЕ:
    SettingsManager должен:
    1. Иметь атрибут city
    2. Загружать его из базы в load_initial_settings
    3. Сохранять его из формы в update_settings
    4. Передавать парсеру
    """)

def main():
    """Главная функция"""
    print("🚀 ДИАГНОСТИКА ПРОБЛЕМЫ ГОРОДА В SETTINGS MANAGER")
    print("="*60)

    check_settings_manager_structure()
    check_database_direct()
    check_views_file()
    create_test_fix()
    check_current_city_flow()

    print("\n" + "="*60)
    print("🎯 КОНКРЕТНЫЕ ШАГИ ДЛЯ ИСПРАВЛЕНИЯ")
    print("="*60)
    print("""
    ШАГ 1: Проверьте SettingsManager
    ---------------------------------
    1. Откройте файл: apps/parsing/core/settings_manager.py
    2. Найдите класс SettingsManager
    3. Проверьте есть ли в __init__: self.city = "Москва"
    4. Найдите метод load_initial_settings
    5. Проверьте загружается ли там город из базы
    
    ШАГ 2: Добавьте недостающий код
    --------------------------------
    Если атрибут city отсутствует, добавьте в __init__:
        self.city = "Москва"  # Значение по умолчанию
    
    В load_initial_settings добавьте:
        # После загрузки user_settings
        if user_settings:
            self.city = getattr(user_settings, 'city', 'Москва')
    
    В update_settings добавьте:
        if 'city' in settings_data:
            self.city = settings_data['city']
    
    ШАГ 3: Проверьте views.py
    --------------------------
    1. Откройте apps/website/views.py
    2. Найдите функцию сохранения настроек
    3. Убедитесь что city берется из request.POST
    4. Убедитесь что передается в sm.update_settings()
    
    ШАГ 4: Запустите тест
    ---------------------
    Запустите: python test_settings_manager.py
    Убедитесь что город загружается и сохраняется правильно
    
    ШАГ 5: Проверьте в браузере
    ---------------------------
    1. Откройте настройки парсера
    2. Измените город на 'Пенза'
    3. Сохраните
    4. Проверьте Network вкладку - отправляется ли city
    5. Перезагрузите страницу - сохранился ли город?
    """)

    print("\n⚠️  ЗАПУСТИТЕ СКОМПИЛИРОВАННЫЙ ТЕСТ:")
    print("python test_settings_manager.py")

if __name__ == "__main__":
    main()