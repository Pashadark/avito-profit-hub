# test_all_proxies.py
import requests
import time
import random
import sys
import os
from dotenv import load_dotenv

load_dotenv()


def test_proxy(proxy_url, name):
    """Тестирует прокси на Avito"""
    try:
        proxies = {'http': proxy_url, 'https': proxy_url}

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9'
        }

        start = time.time()
        response = requests.get(
            'https://www.avito.ru/moskva',
            headers=headers,
            proxies=proxies,
            timeout=10
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            # Проверяем, что это реальная страница Avito
            if 'data-marker="item"' in response.text:
                items_count = response.text.count('data-marker="item"')
                return True, f"✅ РАБОТАЕТ! {items_count} товаров ({elapsed:.2f}с)"
            elif 'доступ ограничен' in response.text.lower():
                return False, "❌ БЛОКИРОВКА Avito"
            else:
                return False, f"⚠️ Не Avito страница ({elapsed:.2f}с)"
        elif response.status_code == 429:
            return False, "❌ 429 Too Many Requests"
        elif response.status_code == 403:
            return False, "❌ 403 Forbidden"
        else:
            return False, f"❌ Статус {response.status_code} ({elapsed:.2f}с)"

    except requests.exceptions.ConnectTimeout:
        return False, "❌ Таймаут подключения"
    except requests.exceptions.ReadTimeout:
        return False, "❌ Таймаут чтения"
    except requests.exceptions.ProxyError:
        return False, "❌ Ошибка прокси"
    except requests.exceptions.ConnectionError:
        return False, "❌ Ошибка соединения"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)[:50]}"


def get_proxy_list():
    """Создает список всех прокси для теста"""
    proxies = []

    # Мобильные прокси
    mobile_http = os.getenv('MOBILE_PROXY_HTTP')
    if mobile_http:
        proxies.append(('Mobile HTTP', mobile_http))

    mobile_socks5 = os.getenv('MOBILE_PROXY_SOCKS5')
    if mobile_socks5:
        proxies.append(('Mobile SOCKS5', mobile_socks5))

    # ProxyMarket аккаунт 1
    user1 = os.getenv('PROXYMARKET_USER1')
    pass1 = os.getenv('PROXYMARKET_PASS1')
    if user1 and pass1:
        # Тестируем первые 10 портов
        for port in range(10000, 10010):
            proxy_url = f'http://{user1}:{pass1}@pool.proxy.market:{port}'
            proxies.append((f'ProxyMarket {port}', proxy_url))

    # ProxyMarket аккаунт 2
    user2 = os.getenv('PROXYMARKET_USER2')
    pass2 = os.getenv('PROXYMARKET_PASS2')
    if user2 and pass2:
        # Тестируем первые 10 портов
        for port in range(10050, 10060):
            proxy_url = f'http://{user2}:{pass2}@pool.proxy.market:{port}'
            proxies.append((f'ProxyMarket {port}', proxy_url))

    # Бесплатные прокси
    free_proxies = [
        ('Free US', 'http://45.77.56.109:3128'),
        ('Free SG', 'http://103.152.112.145:80'),
        ('Free DE', 'http://194.169.167.5:8080'),
        ('Free RU', 'http://193.56.255.230:3128'),
        ('Free NL', 'http://185.162.231.189:80'),
    ]

    proxies.extend(free_proxies)

    return proxies


def main():
    print("=" * 70)
    print("🔥 ТЕСТ ВСЕХ ПРОКСИ НА AVITO")
    print("=" * 70)

    all_proxies = get_proxy_list()
    print(f"\n📋 Всего прокси для теста: {len(all_proxies)}")

    working_proxies = []
    failed_proxies = []

    for i, (name, proxy_url) in enumerate(all_proxies, 1):
        print(f"\n{i:3d}. Тестирую {name}...")
        print(f"    URL: {proxy_url[:60]}...")

        success, message = test_proxy(proxy_url, name)

        if success:
            print(f"    {message}")
            working_proxies.append((name, proxy_url, message))
        else:
            print(f"    {message}")
            failed_proxies.append((name, proxy_url, message))

        # Пауза между запросами
        time.sleep(random.uniform(1, 2))

    # Результаты
    print("\n" + "=" * 70)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"✅ Рабочих: {len(working_proxies)}")
    print(f"❌ Не рабочих: {len(failed_proxies)}")

    if working_proxies:
        print("\n🎉 РАБОЧИЕ ПРОКСИ:")
        for name, proxy_url, message in working_proxies[:10]:  # Покажем первые 10
            print(f"  • {name}: {message}")

        # Сохраним рабочие прокси в файл
        with open('working_proxies.txt', 'w', encoding='utf-8') as f:
            f.write("# Рабочие прокси для Avito\n")
            for name, proxy_url, message in working_proxies:
                f.write(f"{proxy_url}  # {name} - {message}\n")

        print(f"\n💾 Список рабочих прокси сохранен в working_proxies.txt")

    if failed_proxies:
        print("\n🚫 НЕ РАБОЧИЕ ПРОКСИ (первые 10):")
        for name, proxy_url, message in failed_proxies[:10]:
            print(f"  • {name}: {message}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()