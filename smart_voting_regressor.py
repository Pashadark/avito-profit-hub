#!/usr/bin/env python3
"""
Скрипт проверки AvitoParser - тестируем поиск товаров
"""

import sys
import os
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Добавляем путь к проекту
current_dir = os.getcwd()
sys.path.insert(0, current_dir)


async def test_avito_parser():
    print('=' * 80)
    print('ТЕСТИРОВАНИЕ AVITO ПАРСЕРА')
    print('=' * 80)

    try:
        # Импортируем AvitoParser
        from apps.parsing.sites.avito_parser import AvitoParser

        print('1. ✅ AvitoParser импортирован успешно')

        # Создаем драйвер
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Режим без GUI
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=chrome_options)
        print('2. ✅ Selenium WebDriver создан')

        # Создаем парсер
        parser = AvitoParser(driver=driver)
        print('3. ✅ AvitoParser экземпляр создан')
        print(f'   Город: {parser.city}')
        print(f'   Site name: {parser.site_name}')
        print(f'   Base URL: {parser.base_url}')

        # Проверяем метод search_items
        print('\n4. Тестируем метод search_items...')
        try:
            results = await parser.search_items('Туфли')
            print(f'   ✅ Метод search_items выполнен успешно')
            print(f'   Найдено товаров: {len(results)}')

            if results:
                print('   Пример товара:')
                for i, item in enumerate(results[:3]):  # Покажем первые 3
                    print(f'   [{i + 1}] {item.get("title", "Без названия")[:50]} - {item.get("price", 0)}₽')
            else:
                print('   ℹ️ Товары не найдены (может быть нет интернета или Avito блокирует)')

        except Exception as e:
            print(f'   ❌ Ошибка в search_items: {e}')
            import traceback
            traceback.print_exc()

        # Проверяем метод build_search_url
        print('\n5. Тестируем build_search_url...')
        try:
            url = parser.build_search_url('Туфли')
            print(f'   ✅ URL построен: {url[:80]}...')
        except Exception as e:
            print(f'   ❌ Ошибка в build_search_url: {e}')

        # Закрываем драйвер
        driver.quit()
        print('\n6. ✅ Драйвер закрыт')

        print('\n' + '=' * 80)
        print('ТЕСТ ЗАВЕРШЕН')
        print('=' * 80)

    except ImportError as e:
        print(f'❌ Ошибка импорта: {e}')
        print('Проверь пути или установи зависимости')
    except Exception as e:
        print(f'❌ Критическая ошибка: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Запускаем асинхронный тест
    asyncio.run(test_avito_parser())