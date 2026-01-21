from abc import ABC, abstractmethod
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BaseSiteParser(ABC):
    """Базовый класс для парсеров сайтов"""

    def __init__(self, driver):
        self.driver = driver

    @abstractmethod
    async def parse_search_results(self, query):
        """Парсит результаты поиска"""
        pass

    @abstractmethod
    async def parse_item(self, item, category):
        """Парсит отдельный товар"""
        pass

    @abstractmethod
    async def get_product_details(self, product):
        """Получает детальную информацию о товаре"""
        pass

    # 🔥 ДОБАВИТЬ ЭТОТ МЕТОД - ОН ДОЛЖЕН БЫТЬ В АБСТРАКТНОМ КЛАССЕ
    @abstractmethod
    async def search_items(self, query, **kwargs):
        """Поиск товаров по запросу - ОСНОВНОЙ МЕТОД"""
        pass

    def wait_for_element(self, selector, timeout=10):
        """Ожидает появления элемента"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except:
            return None

    def find_element_with_selectors(self, selectors):
        """Ищет элемент по нескольким селекторам"""
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.text.strip():
                    return element
            except:
                continue
        return None

    def find_elements_with_selectors(self, selectors):
        """Ищет элементы по нескольким селекторам"""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return elements
            except:
                continue
        return []