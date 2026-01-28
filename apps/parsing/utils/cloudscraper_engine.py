# 📁 apps/parsing/utils/cloudscraper_engine.py
import cloudscraper
import logging
import re
import time
import random
import os
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger('parser.cloudscraper')


# 🔥 ЗАГРУЗКА ДАННЫХ ИЗ .env
def load_proxy_data_from_env():
    """Загружает данные прокси из .env файла"""
    return {
        'MOBILE_PROXY_HTTP': os.getenv('MOBILE_PROXY_HTTP'),
        'MOBILE_PROXY_SOCKS5': os.getenv('MOBILE_PROXY_SOCKS5'),
        'PROXYMARKET_USER1': os.getenv('PROXYMARKET_USER1'),
        'PROXYMARKET_PASS1': os.getenv('PROXYMARKET_PASS1'),
        'PROXYMARKET_USER2': os.getenv('PROXYMARKET_USER2'),
        'PROXYMARKET_PASS2': os.getenv('PROXYMARKET_PASS2'),
        'PROXY_CHANGE_LOGIN': os.getenv('PROXY_CHANGE_LOGIN'),
        'PROXY_CHANGE_PASSWORD': os.getenv('PROXY_CHANGE_PASSWORD'),
    }


class ProxyManager:
    """УМНЫЙ МЕНЕДЖЕР ПРОКСИ С АВТОРОТАЦИЕЙ"""

    def __init__(self):
        # 🔥 ЗАГРУЗКА ДАННЫХ ИЗ .env
        proxy_data = load_proxy_data_from_env()

        # 🔥 ВСЕ НАШИ ПРОКСИ (берём из .env + бесплатные для теста)
        self.proxy_pool = self._build_proxy_pool(proxy_data)

        self.current_proxy_index = 0
        self.max_fails_before_block = int(os.getenv('PARSER_MAX_RETRIES', 3))
        self.proxy_timeout = int(os.getenv('PARSER_TIMEOUT', 20))

        logger.info(f"✅ ProxyManager инициализирован: {len(self.proxy_pool)} прокси")
        self._log_proxy_status()

    def _build_proxy_pool(self, proxy_data):
        """Строит пул прокси из данных .env + бесплатных"""
        proxy_pool = []

        # 🔥 ПРЕМИУМ ПРОКСИ ИЗ .env (если есть)
        # Мобильные прокси Москва (Мегафон)
        mobile_http = proxy_data.get('MOBILE_PROXY_HTTP')
        if mobile_http:
            proxy_pool.append({
                'name': 'Mobile Moscow Megafon',
                'url': mobile_http,
                'type': 'premium_mobile',
                'geo': 'Москва',
                'operator': 'Megafon',
                'priority': 10,  # Высокий приоритет
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            })

        # SOCKS5 версия
        mobile_socks5 = proxy_data.get('MOBILE_PROXY_SOCKS5')
        if mobile_socks5:
            proxy_pool.append({
                'name': 'Mobile Moscow SOCKS5',
                'url': mobile_socks5,
                'type': 'premium_socks5',
                'geo': 'Москва',
                'operator': 'Megafon',
                'priority': 9,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            })

        # 🔥 PROXY.MARKET ПУЛ - 10000-10999 ПОРТОВ!
        proxymarket_user1 = proxy_data.get('PROXYMARKET_USER1')
        proxymarket_pass1 = proxy_data.get('PROXYMARKET_PASS1')
        proxymarket_user2 = proxy_data.get('PROXYMARKET_USER2')
        proxymarket_pass2 = proxy_data.get('PROXYMARKET_PASS2')

        # ПЕРВЫЙ АККАУНТ (Bf5Bok2pTLp7) - первые 50 портов
        if proxymarket_user1 and proxymarket_pass1:
            for port in range(10000, 10050):
                proxy_pool.append({
                    'name': f'ProxyMarket User1:{port}',
                    'url': f'http://{proxymarket_user1}:{proxymarket_pass1}@pool.proxy.market:{port}',
                    'type': 'proxy_market_pool',
                    'geo': 'RU',
                    'operator': 'ProxyMarket',
                    'priority': 8,
                    'last_used': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'blocked': False
                })

        # ВТОРОЙ АККАУНТ (eIqYgUe7Yybs) - следующие 50 портов
        if proxymarket_user2 and proxymarket_pass2:
            for port in range(10050, 10100):
                proxy_pool.append({
                    'name': f'ProxyMarket User2:{port}',
                    'url': f'http://{proxymarket_user2}:{proxymarket_pass2}@pool.proxy.market:{port}',
                    'type': 'proxy_market_pool',
                    'geo': 'RU',
                    'operator': 'ProxyMarket',
                    'priority': 7,
                    'last_used': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'blocked': False
                })

        # 🔥 БЕСПЛАТНЫЕ ПРОКСИ ДЛЯ ТЕСТИРОВАНИЯ
        proxy_pool.extend(self._get_free_proxies_for_testing())

        # 🔥 РЕЗЕРВНЫЙ: без прокси
        proxy_pool.append({
            'name': 'DIRECT (без прокси)',
            'url': None,
            'type': 'direct',
            'geo': 'Прямое',
            'operator': 'Local IP',
            'priority': 1,
            'last_used': 0,
            'success_count': 0,
            'fail_count': 0,
            'blocked': False
        })

        return proxy_pool

    def _get_free_proxies_for_testing(self):
        """Возвращает список бесплатных прокси для тестирования"""
        return [
            {
                'name': 'FreeProxy #1 (US)',
                'url': 'http://45.77.56.109:3128',
                'type': 'free_http',
                'geo': 'USA',
                'operator': 'FreeProxy',
                'priority': 6,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #2 (SG)',
                'url': 'http://103.152.112.145:80',
                'type': 'free_http',
                'geo': 'Singapore',
                'operator': 'FreeProxy',
                'priority': 5,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #3 (DE)',
                'url': 'http://194.169.167.5:8080',
                'type': 'free_http',
                'geo': 'Germany',
                'operator': 'FreeProxy',
                'priority': 5,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #4 (RU)',
                'url': 'http://193.56.255.230:3128',
                'type': 'free_http',
                'geo': 'Russia',
                'operator': 'FreeProxy',
                'priority': 5,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #5 (NL)',
                'url': 'http://185.162.231.189:80',
                'type': 'free_http',
                'geo': 'Netherlands',
                'operator': 'FreeProxy',
                'priority': 5,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #6 (FR)',
                'url': 'http://51.159.115.233:3128',
                'type': 'free_http',
                'geo': 'France',
                'operator': 'FreeProxy',
                'priority': 4,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #7 (UK)',
                'url': 'http://51.89.15.86:8080',
                'type': 'free_http',
                'geo': 'UK',
                'operator': 'FreeProxy',
                'priority': 4,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #8 (CA)',
                'url': 'http://142.93.113.142:3128',
                'type': 'free_http',
                'geo': 'Canada',
                'operator': 'FreeProxy',
                'priority': 4,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #9 (JP)',
                'url': 'http://133.18.201.195:8080',
                'type': 'free_http',
                'geo': 'Japan',
                'operator': 'FreeProxy',
                'priority': 4,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            },
            {
                'name': 'FreeProxy #10 (IN)',
                'url': 'http://103.216.82.18:6666',
                'type': 'free_http',
                'geo': 'India',
                'operator': 'FreeProxy',
                'priority': 3,
                'last_used': 0,
                'success_count': 0,
                'fail_count': 0,
                'blocked': False
            }
        ]

    def _log_proxy_status(self):
        """Логирует статус всех прокси"""
        logger.info(
            f"📊 СТАТУС ПРОКСИ: {len([p for p in self.proxy_pool if not p['blocked']])}/{len(self.proxy_pool)} активны")

        # Группируем по типу для краткости
        type_stats = {}
        for proxy in self.proxy_pool:
            proxy_type = proxy['type']
            if proxy_type not in type_stats:
                type_stats[proxy_type] = {'total': 0, 'active': 0}
            type_stats[proxy_type]['total'] += 1
            if not proxy['blocked']:
                type_stats[proxy_type]['active'] += 1

        for proxy_type, stats in type_stats.items():
            logger.info(f"  {proxy_type}: {stats['active']}/{stats['total']} активны")

    def get_next_proxy(self) -> Optional[Dict]:
        """Возвращает следующий рабочий прокси"""
        # Сортируем по приоритету и времени последнего использования
        available_proxies = [
            p for p in self.proxy_pool
            if not p['blocked']
        ]

        if not available_proxies:
            logger.error("❌ Нет доступных прокси, все заблокированы!")
            return None

        # Выбираем прокси с наименьшим временем использования и высоким приоритетом
        available_proxies.sort(key=lambda x: (x['last_used'], -x['priority']))
        proxy = available_proxies[0]

        # Обновляем статистику
        proxy['last_used'] = time.time()
        self.current_proxy_index = self.proxy_pool.index(proxy)

        logger.info(f"🔄 Выбран прокси: {proxy['name']} ({proxy['geo']})")

        if proxy['url']:
            return {
                'http': proxy['url'],
                'https': proxy['url']
            }
        else:
            return None  # Прямое подключение

    def mark_success(self, items_found: int = 0):
        """Отмечаем успешное использование прокси"""
        proxy = self.proxy_pool[self.current_proxy_index]
        proxy['success_count'] += 1

        if items_found > 0:
            proxy['priority'] = min(10, proxy['priority'] + 1)  # Повышаем приоритет
            logger.info(f"✅ Прокси {proxy['name']} успешен (товаров: {items_found}), приоритет: {proxy['priority']}")
        else:
            logger.info(f"⚠️ Прокси {proxy['name']} вернул 0 товаров")

    def mark_failed(self, reason: str = "unknown"):
        """Отмечаем неудачное использование прокси"""
        proxy = self.proxy_pool[self.current_proxy_index]
        proxy['fail_count'] += 1

        logger.warning(f"❌ Прокси {proxy['name']} не удался: {reason}")

        # Если много фейлов - блокируем
        if proxy['fail_count'] >= self.max_fails_before_block:
            proxy['blocked'] = True
            proxy['priority'] = 0
            logger.error(f"🚫 Прокси {proxy['name']} заблокирован после {proxy['fail_count']} фейлов")

    def mark_blocked_by_avito(self):
        """Отмечаем что Avito заблокировал этот прокси"""
        proxy = self.proxy_pool[self.current_proxy_index]
        proxy['blocked'] = True
        proxy['priority'] = 0

        logger.error(f"🚫 Avito заблокировал прокси: {proxy['name']}")

    def rotate_ip_for_mobile_proxy(self):
        """Меняет IP для мобильных прокси (если поддерживается)"""
        try:
            proxy_data = load_proxy_data_from_env()
            login = proxy_data.get('PROXY_CHANGE_LOGIN')
            password = proxy_data.get('PROXY_CHANGE_PASSWORD')

            if not login or not password:
                logger.warning("⚠️ Данные для смены IP не указаны в .env")
                return False

            # Для mobileproxy.space
            change_url = "https://mobileproxy.space/api/v1/change_ip"
            params = {'login': login, 'password': password}

            response = requests.get(change_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                new_ip = data.get('new_ip', 'неизвестен')
                logger.info(f"🔄 IP изменен для Mobile Moscow: {new_ip}")

                # Разблокируем прокси после смены IP
                for proxy in self.proxy_pool:
                    if 'mobile' in proxy['type']:
                        proxy['blocked'] = False
                        proxy['fail_count'] = 0

                return True
        except Exception as e:
            logger.debug(f"⚠️ Не удалось сменить IP: {e}")

        return False

    def get_status_report(self) -> str:
        """Возвращает отчет о статусе прокси"""
        total = len(self.proxy_pool)
        active = len([p for p in self.proxy_pool if not p['blocked']])
        blocked = total - active

        report = [
            f"📊 ОТЧЕТ ПРОКСИ: {active}/{total} активны",
            f"🟢 Активные: {active} | 🔴 Заблокированные: {blocked}"
        ]

        # Группируем по типу
        type_stats = {}
        for proxy in self.proxy_pool:
            proxy_type = proxy['type']
            if proxy_type not in type_stats:
                type_stats[proxy_type] = {'total': 0, 'active': 0}
            type_stats[proxy_type]['total'] += 1
            if not proxy['blocked']:
                type_stats[proxy_type]['active'] += 1

        for proxy_type, stats in type_stats.items():
            report.append(f"  {proxy_type}: {stats['active']}/{stats['total']} активны")

        return "\n".join(report)


class CloudscraperEngine:
    """УЛУЧШЕННЫЙ CLOUDSCRAPER С АВТОМАТИЧЕСКОЙ РОТАЦИЕЙ ПРОКСИ"""

    def __init__(self, user_agent: Optional[str] = None, city: str = "Москва"):
        try:
            logger.info(f"🚀 Инициализация CloudscraperEngine для {city}")

            # 🔥 УМНЫЙ МЕНЕДЖЕР ПРОКСИ
            self.proxy_manager = ProxyManager()

            # 🔥 ОПТИМИЗИРОВАННЫЙ CLOUDSCRAPER
            self.scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                },
                delay=random.uniform(4, 7),
                interpreter='js2py',
                debug=False
            )

            # Заголовки как у реального браузера
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1'
            }

            self.city = city
            self.max_retries = int(os.getenv('PARSER_MAX_RETRIES', 3))
            self.request_timeout = int(os.getenv('PARSER_TIMEOUT', 25))

            logger.info(
                f"✅ CloudscraperEngine готов. Автоматическая ротация {len(self.proxy_manager.proxy_pool)} прокси")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации CloudscraperEngine: {e}")
            raise

    def fetch_page_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """Получает страницу с автоматической ротацией прокси при ошибках"""
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                # Получаем следующий прокси
                proxies = self.proxy_manager.get_next_proxy()
                proxy_name = self.proxy_manager.proxy_pool[
                    self.proxy_manager.current_proxy_index
                ]['name']

                if proxies is None and retry_count == 0:
                    logger.info("🌐 Прямое подключение (без прокси)")
                elif proxies:
                    logger.info(f"🔗 Использую прокси: {proxy_name}")

                # Добавляем реферер
                headers = self.headers.copy()
                headers['Referer'] = 'https://www.avito.ru/'

                # Случайная задержка перед запросом
                time.sleep(random.uniform(0.5, 2.0))

                start_time = time.time()

                # Делаем запрос
                response = self.scraper.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.request_timeout
                )

                elapsed = time.time() - start_time

                result = {
                    'html': response.text,
                    'status_code': response.status_code,
                    'url': response.url,
                    'elapsed_time': elapsed,
                    'engine': 'cloudscraper',
                    'proxy_used': proxy_name,
                    'proxied': proxies is not None
                }

                # Анализ ответа
                if self._is_blocked(response.text):
                    result['blocked'] = True
                    result['blocked_reason'] = self._detect_block_reason(response.text)

                    logger.warning(
                        f"🚫 Блокировка через {proxy_name}: {result['blocked_reason']} "
                        f"({elapsed:.2f}с, статус: {response.status_code})"
                    )

                    # Помечаем прокси как заблокированный
                    self.proxy_manager.mark_blocked_by_avito()

                    # Пробуем следующий прокси
                    retry_count += 1
                    continue

                # Успех!
                result['blocked'] = False

                # Считаем товары
                items_count = response.text.count('data-marker="item"')
                result['items_count'] = items_count

                if items_count > 0:
                    logger.info(
                        f"✅ Успех через {proxy_name}: {items_count} товаров "
                        f"({elapsed:.2f}с)"
                    )
                    self.proxy_manager.mark_success(items_count)
                else:
                    logger.warning(
                        f"⚠️ {proxy_name}: 0 товаров ({elapsed:.2f}с, статус: {response.status_code})"
                    )
                    self.proxy_manager.mark_success(0)

                return result

            except Exception as e:
                logger.error(f"💥 Ошибка через {proxy_name}: {e}")
                self.proxy_manager.mark_failed(str(e))
                retry_count += 1
                time.sleep(2)  # Пауза перед следующей попыткой

        # Все попытки исчерпаны
        logger.error(f"❌ Все попытки ({self.max_retries}) исчерпаны для {url}")

        # Пробуем сменить IP для мобильных прокси
        logger.info("🔄 Пробую сменить IP для мобильных прокси...")
        if self.proxy_manager.rotate_ip_for_mobile_proxy():
            logger.info("🔄 IP изменен, пробую еще раз...")
            # Последняя попытка после сменя IP
            try:
                proxies = self.proxy_manager.get_next_proxy()
                response = self.scraper.get(url, headers=self.headers,
                                            proxies=proxies, timeout=self.request_timeout)

                if response.status_code == 200 and not self._is_blocked(response.text):
                    items = response.text.count('data-marker="item"')
                    logger.info(f"🎉 Успех после смены IP: {items} товаров")
                    return {
                        'html': response.text,
                        'status_code': 200,
                        'items_count': items,
                        'proxy_used': 'MOBILE (новый IP)',
                        'proxied': True
                    }
            except:
                pass

        return None

    def _is_blocked(self, html: str) -> bool:
        """Определяет блокировку Avito"""
        if not html or len(html) < 100:
            return True

        html_lower = html.lower()

        # Явные признаки блокировки
        blocked_indicators = [
            'доступ ограничен',
            'проблемы с ip',
            'qrator',
            '403 forbidden',
            'captcha',
            'подтвердите что вы не робот',
            'checking your browser',
            'сеть tor',
            'автоматические запросы'
        ]

        # Признаки успешной страницы Avito
        success_indicators = [
            'data-marker="item"',
            'iva-item-root',
            'avito.ru/items/',
            'объявления'
        ]

        is_blocked = any(indicator in html_lower for indicator in blocked_indicators)
        has_content = any(indicator in html for indicator in success_indicators)

        # Если страница слишком маленькая или нет контента Avito
        if len(html) < 50000 and 'avito' not in html_lower:
            return True

        return is_blocked or not has_content

    def _detect_block_reason(self, html: str) -> str:
        """Определяет причину блокировки"""
        html_lower = html.lower()

        if 'qrator' in html_lower:
            return 'QRATOR (прокси детект)'
        elif 'captcha' in html_lower:
            return 'CAPTCHA'
        elif 'доступ ограничен' in html_lower:
            return 'Avito блокировка'
        elif 'checking your browser' in html_lower:
            return 'Cloudflare'
        elif '403' in html_lower:
            return '403 Forbidden'
        elif 'tor' in html_lower:
            return 'TOR сеть'
        else:
            return 'Неизвестная блокировка'

    def search_items_fast(self, query: str, max_pages: int = 2, **kwargs) -> Optional[Dict]:
        """Быстрый поиск с автоматической ротацией прокси"""
        max_pages = min(max_pages, int(os.getenv('PARSER_MAX_PAGES', 2)))

        logger.info(f"🔍 Поиск '{query}' с ротацией прокси...")

        all_items = []
        successful_pages = 0

        for page in range(1, max_pages + 1):
            url = self.build_search_url(query, page=page, **kwargs)
            logger.info(f"📄 Страница {page}/{max_pages}")

            result = self.fetch_page_with_retry(url)

            if result is None:
                logger.warning(f"⚠️ Не удалось получить страницу {page}")
                break

            if result.get('blocked'):
                logger.warning(f"🚫 Страница {page} заблокирована: {result.get('blocked_reason')}")
                break

            if not result.get('html'):
                logger.warning(f"⚠️ Пустой HTML на странице {page}")
                continue

            # Парсим товары
            items = self._parse_html_advanced(result['html'], query)
            if items:
                all_items.extend(items)
                successful_pages += 1
                logger.info(f"   ✅ Найдено товаров: {len(items)} (через {result.get('proxy_used', '?')})")

            # Пауза между страницами
            time.sleep(random.uniform(1.5, 3.0))

        # Отчет о прокси
        logger.info("\n" + self.proxy_manager.get_status_report())

        return {
            'items': all_items,
            'total_pages': max_pages,
            'successful_pages': successful_pages,
            'engine': 'cloudscraper',
            'proxied': True,
            'success': len(all_items) > 0,
            'total_items': len(all_items),
            'proxy_report': self.proxy_manager.get_status_report()
        }

    def build_search_url(self, query: str, page: int = 1, **kwargs) -> str:
        """Строит URL для поиска"""
        city_map = {
            'москва': 'moskva',
            'санкт-петербург': 'sankt-peterburg',
            'новосибирск': 'novosibirsk',
            'екатеринбург': 'ekaterinburg',
            'казань': 'kazan'
        }

        city_part = city_map.get(self.city.lower(), 'moskva')
        encoded_query = quote_plus(query)

        url = f"https://www.avito.ru/{city_part}?q={encoded_query}&s=104"

        if kwargs.get('min_price'):
            url += f"&pmin={int(kwargs['min_price'])}"
        if kwargs.get('max_price'):
            url += f"&pmax={int(kwargs['max_price'])}"
        if page > 1:
            url += f"&p={page}"

        return url

    def _parse_html_advanced(self, html: str, query: str) -> list:
        """Парсинг HTML (упрощенный для теста)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            items = []

            # Ищем карточки товаров
            elements = soup.select('[data-marker="item"]')

            for elem in elements[:20]:  # Ограничиваем для скорости
                try:
                    # Заголовок
                    title_elem = elem.select_one('[data-marker="item-title"]')
                    title = title_elem.get_text(strip=True) if title_elem else ""

                    # Цена
                    price_elem = elem.select_one('[data-marker="item-price"]')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price = self._parse_price(price_text)

                    # Ссылка
                    link_elem = elem.select_one('a[data-marker="item-title"]')
                    link = link_elem.get('href') if link_elem else ""
                    if link and not link.startswith('http'):
                        link = f"https://www.avito.ru{link}"

                    if title and price > 0:
                        items.append({
                            'name': title[:150],
                            'price': price,
                            'url': link,
                            'query': query,
                            'city': self.city
                        })

                except Exception as e:
                    continue

            return items

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга HTML: {e}")
            return []

    def _parse_price(self, price_text: str) -> int:
        """Парсит цену"""
        try:
            digits = ''.join(filter(str.isdigit, price_text))
            return int(digits) if digits else 0
        except:
            return 0


# 🔥 БЫСТРЫЙ ТЕСТ НОВОЙ СИСТЕМЫ
if __name__ == "__main__":
    import sys

    # 🔥 ЗАГРУЗКА .env ПЕРЕД ТЕСТОМ
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('proxy_rotator.log', encoding='utf-8')
        ]
    )

    print("=" * 70)
    print("🔥 ТЕСТ АВТОМАТИЧЕСКОЙ РОТАЦИИ ПРОКСИ (данные из .env)")
    print("=" * 70)

    # Покажем какие данные загрузились
    proxy_data = load_proxy_data_from_env()
    print(f"\n📋 ЗАГРУЖЕННЫЕ ПРОКСИ:")
    for key, value in proxy_data.items():
        if value and 'PASSWORD' not in key and 'PASS' not in key:
            print(f"  ✅ {key}: {value[:20]}...")
        elif value:
            print(f"  ✅ {key}: *** (скрыто)")

    engine = CloudscraperEngine(city="Москва")

    # Тестовый поиск
    result = engine.search_items_fast("iPhone", max_pages=1)

    if result and result.get('success'):
        print(f"\n🎉 УСПЕХ! Найдено товаров: {result['total_items']}")
        print(f"📊 Страниц обработано: {result['successful_pages']}/{result['total_pages']}")

        # Покажем первый товар
        if result['items']:
            item = result['items'][0]
            print(f"\n📱 Пример товара:")
            print(f"   Название: {item['name'][:80]}...")
            print(f"   Цена: {item['price']}₽")
            print(f"   Город: {item['city']}")
    else:
        print(f"\n😔 Поиск не удался")
        print(f"📋 Отчет: {engine.proxy_manager.get_status_report()}")

    print("\n" + "=" * 70)