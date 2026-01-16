from dataclasses import dataclass
from typing import List


@dataclass
class ParserSettings:
    """Модель настроек парсера"""
    keywords: str = ""
    exclude_keywords: str = ""
    min_price: float = 0
    max_price: float = 100000
    min_rating: float = 4.0
    seller_type: str = 'all'
    check_interval: int = 30
    max_items_per_hour: int = 10
    browser_windows: int = 1
    is_active: bool = True

    def get_search_queries(self) -> List[str]:
        """Возвращает список поисковых запросов"""
        return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]

    def get_exclude_keywords_list(self) -> List[str]:
        """Возвращает список исключаемых слов"""
        if not self.exclude_keywords:
            return []
        return [kw.strip() for kw in self.exclude_keywords.split(',') if kw.strip()]

    def get_keywords_list(self) -> List[str]:
        """Алиас для get_search_queries для совместимости"""
        return self.get_search_queries()

    # 🔥 КЛЮЧЕВОЕ ДОБАВЛЕНИЕ: Свойство keywords_list для прямого доступа
    @property
    def keywords_list(self) -> List[str]:
        """Свойство для прямого доступа к списку ключевых слов"""
        return self.get_keywords_list()