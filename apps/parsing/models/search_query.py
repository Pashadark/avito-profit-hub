from dataclasses import dataclass
from typing import List

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")
        print(f"[SAFE_LOG] {message}")
@dataclass
class SearchQuery:
    """Модель поискового запроса"""
    name: str
    category: str
    target_price: float
    min_price: float = 0
    max_price: float = 1000000
    is_active: bool = True

    def get_keywords(self) -> List[str]:
        """Возвращает ключевые слова из названия"""
        return [kw.strip() for kw in self.name.split(',') if kw.strip()]