"""
Скрипт для диагностики проблемы с городом в парсере
Запуск: python debug_city.py
"""

import os
import sys
import django
import asyncio
import logging

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    django.setup()
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("✅ Django успешно настроен")
except Exception as e:
    print(f"❌ Ошибка настройки Django: {e}")
    sys.exit(1)


def debug_settings():
    """Проверка настроек в базе данных"""
    from apps.website.models import ParserSettings

    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА НАСТРОЕК В БАЗЕ ДАННЫХ")
    print("=" * 60)

    try:
        # Получаем настройки "Пенза1"
        settings = ParserSettings.objects.filter(name="Пенза1").first()
        if settings:
            print(f"✅ Найдены настройки 'Пенза1':")
            print(f"   ID: {settings.id}")
            print(f"   Город: '{settings.city}'")
            print(f"   Сайт: {settings.site}")
            print(f"   Ключевые слова: {settings.keywords}")
            print(f"   Пользователь: {settings.user.username} (ID: {settings.user.id})")
        else:
            print("❌ Настройки 'Пенза1' не найдены")
            # Покажем все настройки пользователя 1
            all_settings = ParserSettings.objects.filter(user_id=1)
            print(f"\nВсе настройки пользователя 1:")
            for s in all_settings:
                print(f"  - {s.name}: город='{s.city}', сайт={s.site}")

    except Exception as e:
        print(f"❌ Ошибка проверки настроек: {e}")


def debug_avito_parser():
    """Проверка Avito парсера"""
    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА AVITO ПАРСЕРА")
    print("=" * 60)

    try:
        from apps.parsing.parser.avito import AvitoParser

        # Создаем драйвер для теста
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Без GUI для скорости
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)

        # Тест 1: Создание парсера с разными городами
        print("\n🎯 ТЕСТ 1: Создание парсера")

        # Тест с городом по умолчанию
        parser_default = AvitoParser(driver)
        print(f"   Город по умолчанию: '{parser_default.city}'")

        # Тест с явным городом
        parser_penza = AvitoParser(driver, city="Пенза")
        print(f"   Город явный: '{parser_penza.city}'")

        # Тест с пустым городом
        parser_empty = AvitoParser(driver, city="")
        print(f"   Город пустой: '{parser_empty.city}'")

        # Тест 2: Перевод города в slug
        print("\n🎯 ТЕСТ 2: Перевод города в slug")

        test_cities = ["Пенза", "Москва", "Санкт-Петербург", "Новосибирск", "", "пенза", "Мск"]

        for city in test_cities:
            try:
                slug = parser_penza.city_translator.get_slug(city)
                print(f"   '{city}' -> '{slug}'")
            except Exception as e:
                print(f"   '{city}' -> ОШИБКА: {e}")

        # Тест 3: Построение URL
        print("\n🎯 ТЕСТ 3: Построение URL")

        parser_penza.city = "Пенза"  # Явно устанавливаем город
        url_penza = parser_penza.build_search_url("телефон")
        print(f"   Пенза: {url_penza[:80]}...")

        parser_default.city = "Москва"
        url_moscow = parser_default.build_search_url("телефон")
        print(f"   Москва: {url_moscow[:80]}...")

        # Тест 4: Проверка city_translator
        print("\n🎯 ТЕСТ 4: Проверка CITY_MAPPING")

        from apps.parsing.parser.avito import CITY_MAPPING
        test_cities_mapping = ["Пенза", "Москва", "Санкт-Петербург", "пенза", "moscow", "moskva"]

        for city in test_cities_mapping:
            city_key = city.capitalize()
            if city_key in CITY_MAPPING:
                print(f"   '{city}' найдено: {CITY_MAPPING[city_key]}")
            else:
                # Проверяем варианты
                found = False
                for rus_name, eng_name in CITY_MAPPING.items():
                    if rus_name.lower() == city.lower():
                        print(f"   '{city}' найдено (регистр): {eng_name}")
                        found = True
                        break
                if not found:
                    print(f"   '{city}' НЕ найдено в CITY_MAPPING")

        driver.quit()

    except Exception as e:
        print(f"❌ Ошибка теста Avito парсера: {e}")
        import traceback
        print(f"❌ Traceback:\n{traceback.format_exc()}")


def debug_selenium_parser():
    """Проверка Selenium парсера"""
    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА SELENIUM ПАРСЕРА")
    print("=" * 60)

    try:
        from apps.parsing.parser.selenium_parser import SeleniumAvitoParser

        # Создаем парсер
        parser = SeleniumAvitoParser()

        # Проверяем атрибуты
        print("\n🎯 АТРИБУТЫ ПАРСЕРА:")
        attrs_to_check = ['current_user_id', 'current_user_username', 'current_site',
                          'search_queries', 'settings_manager']

        for attr in attrs_to_check:
            if hasattr(parser, attr):
                value = getattr(parser, attr)
                print(f"   {attr}: {value}")
            else:
                print(f"   {attr}: НЕТ АТРИБУТА!")

        # Проверяем настройки
        if hasattr(parser, 'settings_manager') and parser.settings_manager:
            print("\n🎯 SETTINGS MANAGER:")
            sm = parser.settings_manager
            sm_attrs = ['city', 'search_queries', 'min_price', 'max_price']

            for attr in sm_attrs:
                if hasattr(sm, attr):
                    value = getattr(sm, attr)
                    print(f"   {attr}: {value}")
                else:
                    print(f"   {attr}: НЕТ АТРИБУТА в settings_manager!")
        else:
            print("❌ settings_manager не найден!")

    except Exception as e:
        print(f"❌ Ошибка теста Selenium парсера: {e}")


def debug_city_flow():
    """Отладка потока передачи города"""
    print("\n" + "=" * 60)
    print("🔍 ОТЛАДКА ПОТОКА ПЕРЕДАЧИ ГОРОДА")
    print("=" * 60)

    # Симуляция потока данных
    print("\n🎯 СИМУЛЯЦИЯ ПОТОКА:")

    # 1. Из базы в модель
    print("1. База -> ParserSettings:")
    print("   SELECT city FROM website_parsersettings WHERE name='Пенза1';")
    print("   Результат: 'Пенза'")

    # 2. Из модели в форму
    print("\n2. ParserSettings -> Форма:")
    print("   form.city.value = settings.city")
    print("   Результат: поле ввода содержит 'Пенза'")

    # 3. Из формы в views.py
    print("\n3. Форма -> views.py (save_settings):")
    print("   request.POST.get('city') = 'Пенза'")

    # 4. Из views.py в settings_manager
    print("\n4. views.py -> settings_manager:")
    print("   settings_manager.city = 'Пенза'")

    # 5. Из settings_manager в парсер
    print("\n5. settings_manager -> SeleniumParser:")
    print("   Парсер получает город из settings_manager?")

    # 6. Из SeleniumParser в AvitoParser
    print("\n6. SeleniumParser -> AvitoParser:")
    print("   AvitoParser(driver, settings_manager, settings_manager.city)")
    print("   ИЛИ: parser.set_city(settings_manager.city)")

    print("\n🔴 ВОЗМОЖНЫЕ МЕСТА ОШИБКИ:")
    print("   1. Форма не отправляет поле 'city'")
    print("   2. settings_manager не сохраняет город")
    print("   3. SeleniumParser не передает город в AvitoParser")
    print("   4. AvitoParser использует город по умолчанию")


def debug_form_submission():
    """Отладка отправки формы"""
    print("\n" + "=" * 60)
    print("🔍 ОТЛАДКА ОТПРАВКИ ФОРМЫ")
    print("=" * 60)

    # Проверяем HTML форму
    print("\n🎯 ПРОВЕРЬТЕ HTML ФОРМУ:")
    print("""
    В файле parser_settings.html убедитесь что:

    1. Поле города есть в форме:
       <input type="text" name="city" id="id_city" ...>

    2. Значение правильное:
       value="{{ form.city.value|default:'Москва' }}"

    3. Форма отправляет данные методом POST:
       <form method="post" id="parserSettingsForm">

    4. Есть CSRF токен:
       {% csrf_token %}

    Проверьте Network вкладку браузера:
    1. Откройте DevTools (F12)
    2. Перейдите на вкладку Network
    3. Сохраните настройки
    4. Посмотрите какие данные отправляются в POST запросе
    5. Должно быть: city=Пенза
    """)


async def debug_parser_creation():
    """Тест создания парсера с городом"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ СОЗДАНИЯ ПАРСЕРА С ГОРОДОМ")
    print("=" * 60)

    try:
        # Имитируем создание парсера как это делает система
        from apps.parsing.parser.selenium_parser import SeleniumAvitoParser
        from apps.parsing.core.settings_manager import SettingsManager

        # Создаем менеджер настроек с городом
        settings_manager = SettingsManager()
        settings_manager.city = "Пенза"  # 🔥 Устанавливаем город

        # Создаем парсер
        parser = SeleniumAvitoParser()

        # Настраиваем парсер
        parser.configure_for_user(1, "test_user")

        # Устанавливаем settings_manager
        parser.settings_manager = settings_manager

        # Проверяем
        print(f"✅ Парсер создан")
        print(f"   Город в settings_manager: {parser.settings_manager.city}")
        print(f"   Текущий сайт: {parser.current_site}")

        # Тест создания AvitoParser через _get_site_parser
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            chrome_options = Options()
            chrome_options.add_argument("--headless")

            driver = webdriver.Chrome(options=chrome_options)

            # Получаем парсер
            site_parser = parser._get_site_parser(driver, "avito")

            print(f"\n✅ AvitoParser создан")
            print(f"   Город в AvitoParser: {site_parser.city}")

            # Проверяем URL
            url = site_parser.build_search_url("телефон")
            print(f"   Построенный URL: {url[:80]}...")

            # Проверяем содержит ли URL Пензу
            if "penza" in url:
                print("   🎉 URL содержит правильный город 'penza'!")
            else:
                print(f"   ❌ URL не содержит 'penza': {url}")

            driver.quit()

        except Exception as e:
            print(f"❌ Ошибка теста AvitoParser: {e}")

    except Exception as e:
        print(f"❌ Ошибка теста создания парсера: {e}")


def check_django_models():
    """Проверка моделей Django"""
    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА МОДЕЛЕЙ DJANGO")
    print("=" * 60)

    from apps.website.models import ParserSettings

    print("\n🎯 СТРУКТУРА МОДЕЛИ ParserSettings:")

    # Получаем поля модели
    fields = ParserSettings._meta.get_fields()
    for field in fields:
        if hasattr(field, 'name'):
            print(f"   {field.name}: {field.get_internal_type()}")

    # Проверяем конкретную запись
    print("\n🎯 ЗАПИСЬ 'Пенза1':")
    settings = ParserSettings.objects.filter(name="Пенза1").first()
    if settings:
        print(f"   id: {settings.id}")
        print(f"   name: {settings.name}")
        print(f"   city: '{settings.city}'")
        print(f"   site: {settings.site}")
        print(f"   keywords: {settings.keywords}")
        print(f"   created_at: {settings.created_at}")
        print(f"   updated_at: {settings.updated_at}")
        print(f"   user_id: {settings.user_id}")
    else:
        print("   ❌ Запись не найдена")


def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 ЗАПУСК ДИАГНОСТИКИ ПРОБЛЕМЫ С ГОРОДОМ")
    print("=" * 60)

    debug_settings()
    debug_avito_parser()
    debug_selenium_parser()
    debug_city_flow()
    debug_form_submission()
    check_django_models()

    # Асинхронные тесты
    asyncio.run(debug_parser_creation())

    print("\n" + "=" * 60)
    print("📋 ВЫВОДЫ:")
    print("=" * 60)
    print("""
    Возможные причины проблемы:

    1. 🔴 Город не передается из формы в views.py
       - Проверьте Network вкладку: отправляется ли city в POST

    2. 🔴 SettingsManager не сохраняет город
       - Проверьте update_settings метод в settings/system.py

    3. 🔴 Парсер не получает город из SettingsManager
       - Проверьте _get_site_parser в selenium_parser.py

    4. 🔴 AvitoParser использует город по умолчанию
       - Проверьте __init__ и build_search_url в avito.py

    5. 🔴 Кэш парсеров не очищается при смене города
       - site_parsers кэшируется без учета города
    """)


if __name__ == "__main__":
    run_all_tests()