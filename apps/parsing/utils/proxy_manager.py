import random
import requests
from datetime import datetime, timedelta


class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_proxy = None
        self.last_rotation = datetime.now()
        self.rotation_interval = timedelta(minutes=30)
        self.bad_proxies = set()

    def load_proxies(self, proxy_list):
        """Загружает список прокси"""
        self.proxies = [p for p in proxy_list if p not in self.bad_proxies]

    def get_proxy(self):
        """Возвращает случайный прокси с ротацией"""
        if not self.proxies:
            return None

        # Ротация каждые 30 минут
        if datetime.now() - self.last_rotation > self.rotation_interval:
            self.current_proxy = random.choice(self.proxies)
            self.last_rotation = datetime.now()

        return self.current_proxy

    def mark_bad_proxy(self, proxy):
        """Помечает прокси как неработающий"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.bad_proxies.add(proxy)
            print(f"Удален неработающий прокси: {proxy}")

    def get_proxy_for_selenium(self):
        """Форматирует прокси для Selenium"""
        proxy = self.get_proxy()
        if proxy:
            return f"http://{proxy}"
        return None


# Расширенная система User-Agent
class UserAgentManager:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 OPR/103.0.0.0'
        ]

    def get_random_user_agent(self):
        return random.choice(self.user_agents)