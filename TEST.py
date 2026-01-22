#!/usr/bin/env python3
"""
🚀 ТЕСТОВЫЙ СКРИПТ ДЛЯ ДИАГНОСТИКИ OFFSET ПРОБЛЕМЫ
Запуск: python test_offset_issue.py
"""

import asyncio
import logging
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('test_offset')


async def test_avito_parser_offset():
    """Тестируем работу AvitoParser с offset"""
    try:
        logger.info("🚀 ЗАПУСК ТЕСТА AVITO PARSER OFFSET...")

        # Импортируем необходимые модули
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from apps.parsing.sites.avito_parser import AvitoParser

        # Настройки Chrome
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")  # Без GUI для теста
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Создаем драйвер
        logger.info("🖥️ Создаю драйвер Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)

        try:
            # Создаем парсер
            logger.info("🔧 Создаю AvitoParser...")
            parser = AvitoParser(driver, city="Москва")

            # Тест 1: Поиск БЕЗ offset
            logger.info("\n" + "=" * 60)
            logger.info("🧪 ТЕСТ 1: Поиск БЕЗ offset (страница 1)")
            logger.info("=" * 60)

            # Открываем главную страницу
            driver.get("https://www.avito.ru")
            await asyncio.sleep(3)

            # Запускаем поиск
            query = "Видеокарта"
            logger.info(f"🔍 Ищу: '{query}' (без offset)")

            try:
                items = await parser.search_items(query, offset=0)
                logger.info(f"✅ Найдено товаров: {len(items)}")

                if items:
                    logger.info(f"📦 Первый товар: {items[0].get('name', 'Нет названия')[:50]}...")
                    logger.info(f"🔗 URL первого товара: {items[0].get('url', 'Нет URL')[:80]}...")

                    # Проверяем текущий URL драйвера
                    current_url = driver.current_url
                    logger.info(f"🌐 Текущий URL драйвера: {current_url}")

                    # Проверяем содержит ли URL параметр p=
                    if "?p=" in current_url or "&p=" in current_url:
                        logger.info("✅ URL содержит параметр пагинации p=")
                    else:
                        logger.info("❌ URL НЕ содержит параметр пагинации p=")
                else:
                    logger.warning("⚠️ Товары не найдены")

            except Exception as e:
                logger.error(f"❌ Ошибка поиска: {e}")

            # Тест 2: Поиск С offset=50 (страница 2)
            logger.info("\n" + "=" * 60)
            logger.info("🧪 ТЕСТ 2: Поиск С offset=50 (страница 2)")
            logger.info("=" * 60)

            logger.info(f"🔍 Ищу: '{query}' (offset=50)")

            try:
                items = await parser.search_items(query, offset=50)
                logger.info(f"✅ Найдено товаров: {len(items)}")

                if items:
                    logger.info(f"📦 Первый товар: {items[0].get('name', 'Нет названия')[:50]}...")
                    logger.info(f"🔗 URL первого товара: {items[0].get('url', 'Нет URL')[:80]}...")

                    # Проверяем текущий URL драйвера
                    current_url = driver.current_url
                    logger.info(f"🌐 Текущий URL драйвера: {current_url}")

                    # Проверяем содержит ли URL параметр p=
                    if "?p=" in current_url or "&p=" in current_url:
                        logger.info("✅ URL содержит параметр пагинации p=")
                        # Извлекаем номер страницы
                        import re
                        match = re.search(r'[?&]p=(\d+)', current_url)
                        if match:
                            page_num = match.group(1)
                            logger.info(f"📄 Номер страницы из URL: {page_num}")
                            expected_page = (50 // 50) + 1  # offset=50 → page=2
                            if int(page_num) == expected_page:
                                logger.info(f"✅ Правильная страница: {page_num} (ожидалось: {expected_page})")
                            else:
                                logger.error(f"❌ Неправильная страница: {page_num} (ожидалось: {expected_page})")
                    else:
                        logger.error("❌ URL НЕ содержит параметр пагинации p=")

                    # Проверяем заголовок страницы
                    page_title = driver.title
                    logger.info(f"📄 Заголовок страницы: {page_title}")

                else:
                    logger.warning("⚠️ Товары не найдены")

            except Exception as e:
                logger.error(f"❌ Ошибка поиска: {e}")

            # Тест 3: Проверяем метод build_search_url
            logger.info("\n" + "=" * 60)
            logger.info("🧪 ТЕСТ 3: Проверка метода build_search_url")
            logger.info("=" * 60)

            try:
                # Получаем URL напрямую из метода
                search_url = parser.build_search_url(query)
                logger.info(f"🔗 URL от build_search_url: {search_url}")

                # Проверяем структуру URL
                if search_url:
                    if "?q=" in search_url:
                        logger.info("✅ URL содержит параметр поиска ?q=")
                    else:
                        logger.error("❌ URL НЕ содержит параметр поиска ?q=")

                    if "&s=104" in search_url:
                        logger.info("✅ URL содержит сортировку &s=104")
                    else:
                        logger.warning("⚠️ URL НЕ содержит сортировку &s=104")

                    # Пробуем добавить пагинацию
                    test_url_with_page = f"{search_url}&p=2"
                    logger.info(f"🔗 Тестовый URL с пагинацией: {test_url_with_page}")
                else:
                    logger.error("❌ build_search_url вернул None!")

            except Exception as e:
                logger.error(f"❌ Ошибка build_search_url: {e}")

            # Тест 4: Проверяем что происходит в search_items
            logger.info("\n" + "=" * 60)
            logger.info("🧪 ТЕСТ 4: Детальная проверка search_items")
            logger.info("=" * 60)

            # Временно переопределим метод для дебага
            original_search_items = parser.search_items

            async def debug_search_items(query, **kwargs):
                logger.info(f"🔍 DEBUG search_items вызван с:")
                logger.info(f"  - query: '{query}'")
                logger.info(f"  - kwargs: {kwargs}")

                offset = kwargs.get('offset', 0)
                logger.info(f"  - offset: {offset}")

                # Вызываем build_search_url
                url = parser.build_search_url(query)
                logger.info(f"  - build_search_url вернул: {url}")

                # Проверяем offset
                if offset > 0:
                    page_num = (offset // 50) + 1
                    logger.info(f"  - offset={offset} → page={page_num}")

                    if url:
                        # Проверяем как добавляется параметр
                        if '?' in url:
                            url_with_page = f"{url}&p={page_num}"
                        else:
                            url_with_page = f"{url}?p={page_num}"
                        logger.info(f"  - URL с пагинацией: {url_with_page}")

                # Вызываем оригинальный метод
                return await original_search_items(query, **kwargs)

            # Временно заменяем метод
            parser.search_items = debug_search_items

            # Запускаем тестовый поиск
            logger.info("\n🔍 Запускаю debug поиск с offset=100...")
            try:
                items = await parser.search_items("Видеокарта", offset=100)
                logger.info(f"✅ Debug поиск завершен. Найдено: {len(items)} товаров")
            except Exception as e:
                logger.error(f"❌ Debug поиск упал: {e}")

        finally:
            # Закрываем драйвер
            logger.info("\n🧹 Закрываю драйвер...")
            driver.quit()

        logger.info("\n" + "=" * 60)
        logger.info("🎯 ТЕСТ ЗАВЕРШЕН")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Критическая ошибка теста: {e}")
        import traceback
        logger.error(f"❌ Трассировка:\n{traceback.format_exc()}")
        return False


async def test_build_search_url_directly():
    """Тестируем метод build_search_url напрямую"""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ПРЯМОЙ ТЕСТ build_search_url")
        logger.info("=" * 60)

        # Импортируем только нужные модули
        from apps.parsing.sites.avito_parser import AvitoParser

        # Создаем заглушку драйвера
        class MockDriver:
            def __init__(self):
                self.current_url = "https://www.avito.ru"

        mock_driver = MockDriver()

        # Создаем парсер
        parser = AvitoParser(mock_driver, city="Москва")

        # Тестируем разные запросы
        test_queries = [
            "Видеокарта",
            "RTX 4090",
            "iPhone 15"
        ]

        for query in test_queries:
            logger.info(f"\n🔍 Тестирую запрос: '{query}'")
            url = parser.build_search_url(query)

            if url:
                logger.info(f"✅ URL: {url}")

                # Проверяем компоненты
                checks = [
                    ("https://www.avito.ru/", "Начинается с правильного домена"),
                    (f"?q={query.replace(' ', '%20')}", "Содержит закодированный запрос"),
                    ("&s=104", "Содержит сортировку по дате")
                ]

                for check_str, check_desc in checks:
                    if check_str in url:
                        logger.info(f"  ✓ {check_desc}")
                    else:
                        logger.error(f"  ✗ {check_desc}")

                # Пробуем добавить пагинацию
                if '?' in url:
                    url_page2 = f"{url}&p=2"
                else:
                    url_page2 = f"{url}?p=2"

                logger.info(f"🔗 URL с пагинацией (p=2): {url_page2}")
            else:
                logger.error(f"❌ build_search_url вернул None для запроса: '{query}'")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка теста build_search_url: {e}")
        return False


async def main():
    """Основная функция теста"""
    logger.info("🚀 ЗАПУСК ДИАГНОСТИКИ OFFSET ПРОБЛЕМЫ")
    logger.info("=" * 60)

    # Тест 1: Проверка build_search_url
    success1 = await test_build_search_url_directly()

    # Тест 2: Полный тест парсера
    success2 = await test_avito_parser_offset()

    # Итоги
    logger.info("\n" + "=" * 60)
    logger.info("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60)
    logger.info(f"✅ build_search_url тест: {'ПРОЙДЕН' if success1 else 'ПРОВАЛЕН'}")
    logger.info(f"✅ AvitoParser тест: {'ПРОЙДЕН' if success2 else 'ПРОВАЛЕН'}")

    if success1 and success2:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        logger.error("❌ ЕСТЬ ПРОБЛЕМЫ В РАБОТЕ OFFSET!")

        # Рекомендации по исправлению
        logger.info("\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        logger.info("1. Проверь метод build_search_url в avito_parser.py")
        logger.info("2. Убедись что offset правильно конвертируется в номер страницы")
        logger.info("3. Проверь что параметр p= правильно добавляется к URL")
        logger.info("4. Убедись что search_items принимает offset параметр")


if __name__ == "__main__":
    # Запускаем тест
    asyncio.run(main())