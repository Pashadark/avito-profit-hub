import requests
import time
from bs4 import BeautifulSoup


def test_avito_speed():
    print("⚡ Тестируем скорость доступа к Avito...")

    # URL для теста (первое объявление из логов)
    test_url = "https://www.avito.ru/penza/odezhda_obuv_aksessuary/tufli_zhenskie_37_razmer_7866518732"

    # 1. Через requests (чистый HTTP)
    start = time.time()
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(test_url, headers=headers, timeout=10)
        requests_time = time.time() - start
        print(f"✅ Requests: {requests_time:.2f} сек, статус: {r.status_code}")
        print(f"   Размер HTML: {len(r.text):,} символов")

        # Проверяем, что это реальная страница товара
        if "туфли" in r.text.lower():
            print("   Контент: найдены товары")
        else:
            print("   ⚠️ Контент: возможно капча или блокировка")

    except Exception as e:
        print(f"❌ Requests ошибка: {e}")

    # 2. Проверяем через Selenium быстро
    print("\n🔧 Тестируем Selenium...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Без GUI
        chrome_options.add_argument("--disable-images")  # Без картинок

        start = time.time()
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(15)

        driver.get(test_url)
        selenium_time = time.time() - start

        print(f"✅ Selenium headless: {selenium_time:.2f} сек")
        print(f"   Заголовок: {driver.title[:50]}...")

        driver.quit()

    except Exception as e:
        print(f"❌ Selenium ошибка: {e}")


if __name__ == "__main__":
    test_avito_speed()