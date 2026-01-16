import re
from typing import List, Tuple, Optional, Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By


class KeywordSearcher:
    """
    Класс для поиска ключевых слов на страницах Avito
    Используется в парсере для фильтрации товаров
    """

    def __init__(self, exclude_keywords: List[str] = None):
        self.exclude_keywords = exclude_keywords or []

    def search_keywords_priority(self, driver, keywords: List[str]) -> Tuple[bool, str, str]:
        """
        Ищет ключевые слова с приоритетом:
        1. Заголовок <h1 itemprop="name">
        2. Описание <h2>Описание</h2>

        Возвращает: (найдено_ли, тип_контента, текст)
        """
        # 1. Поиск в заголовке
        title_match, title_text, title_element = self._search_in_title(driver, keywords)
        if title_match:
            # Проверяем исключаемые слова в заголовке
            if not self._contains_exclude_keywords(title_text):
                return True, "title", title_text

        # 2. Поиск в описании
        desc_match, desc_text = self._search_in_description(driver, keywords)
        if desc_match:
            # Проверяем исключаемые слова в описании
            if not self._contains_exclude_keywords(desc_text):
                return True, "description", desc_text

        return False, "", ""

    def _search_in_title(self, driver, keywords: List[str]) -> Tuple[bool, str, Any]:
        """Поиск ключевых слов в заголовке товара"""
        title_selectors = [
            'h1[itemprop="name"]',
            '[data-marker="item-view/title-info"]',
            '[data-marker="item-title"]',
            '.iva-item-titleStep-_CxvN',
            '.title-root-zZCwT',
            'h1',
            '[itemprop="name"]'
        ]

        for selector in title_selectors:
            try:
                title_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for title_element in title_elements:
                    title_text = title_element.text.strip()
                    if title_text and self._contains_any_keyword(title_text, keywords):
                        return True, title_text, title_element
            except Exception:
                continue

        return False, "", None

    def _search_in_description(self, driver, keywords: List[str]) -> Tuple[bool, str]:
        """Поиск ключевых слов в описании товара"""
        # Сначала находим блок описания
        desc_selectors = [
            '[data-marker="item-view/item-description"]',
            '.item-description-text',
            '.description-text',
            '[itemprop="description"]',
            '.iva-item-text-Ge6dR'
        ]

        for selector in desc_selectors:
            try:
                desc_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for desc_element in desc_elements:
                    description_text = desc_element.text.strip()
                    if description_text and len(description_text) > 10:
                        description_text = ' '.join(description_text.split())

                        if self._contains_any_keyword(description_text, keywords):
                            if len(description_text) > 300:
                                description_text = description_text[:300] + '...'
                            return True, description_text
            except Exception:
                continue

        # Альтернативный поиск: ищем заголовок "Описание" и берем следующий текст
        try:
            desc_headers = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Описание')]")
            for header in desc_headers:
                try:
                    # Пробуем найти следующий текстовый блок
                    next_element = header.find_element(By.XPATH, "following-sibling::*[1]")
                    description_text = next_element.text.strip()
                    if description_text and self._contains_any_keyword(description_text, keywords):
                        if len(description_text) > 300:
                            description_text = description_text[:300] + '...'
                        return True, description_text
                except Exception:
                    continue
        except Exception:
            pass

        return False, ""

    def _contains_any_keyword(self, text: str, keywords: List[str]) -> bool:
        """Проверяет содержит ли текст любой из ключевых слов"""
        if not text or not keywords:
            return False

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords if keyword.strip())

    def _contains_exclude_keywords(self, text: str) -> bool:
        """Проверяет содержит ли текст исключаемые слова"""
        if not text or not self.exclude_keywords:
            return False

        text_lower = text.lower()
        return any(
            exclude_keyword.lower() in text_lower
            for exclude_keyword in self.exclude_keywords
            if exclude_keyword.strip()
        )

    def extract_keywords_from_text(self, text: str, keywords: List[str]) -> List[str]:
        """Извлекает найденные ключевые слова из текста"""
        found_keywords = []
        text_lower = text.lower()

        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        return found_keywords  # ✅ ВОТ ТЕПЕРЬ RETURN ЕСТЬ!

    def smart_search(self, driver, include_keywords: List[str], exclude_keywords: List[str] = None) -> Dict[str, Any]:
        """
        Умный поиск с учетом включения и исключения ключевых слов

        Возвращает детальную информацию о найденном товаре
        """
        exclude_keywords = exclude_keywords or self.exclude_keywords

        found, content_type, text = self.search_keywords_priority(driver, include_keywords)

        if not found:
            return {
                'found': False,
                'reason': 'keywords_not_found'
            }

        # Проверяем исключаемые слова
        if self._contains_exclude_keywords(text):
            return {
                'found': False,
                'reason': 'excluded_keywords_found',
                'content_type': content_type,
                'text_sample': text[:100] + '...' if len(text) > 100 else text
            }

        # Извлекаем конкретные найденные ключевые слова
        found_keywords = self.extract_keywords_from_text(text, include_keywords)

        return {
            'found': True,
            'content_type': content_type,
            'text_sample': text[:200] + '...' if len(text) > 200 else text,
            'found_keywords': found_keywords,
            'text_length': len(text)
        }


# Пример использования
if __name__ == "__main__":
    # Тестирование метода
    searcher = KeywordSearcher()

    # Тест extract_keywords_from_text
    text = "Продам iPhone 13 Pro Max в отличном состоянии"
    keywords = ['iphone', 'samsung', 'pro', 'max']

    result = searcher.extract_keywords_from_text(text, keywords)
    print(f"Найдены ключевые слова: {result}")  # ['iphone', 'pro', 'max']