from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")
        print(f"[SAFE_LOG] {message}")
@dataclass
class Product:
    """Модель товара"""
    name: str
    price: float
    target_price: float
    url: str
    category: str
    description: str = ""
    seller_name: str = ""
    seller_rating: Optional[float] = None
    reviews_count: int = 0
    avito_category: str = ""
    city: str = "Москва"
    image_url: Optional[str] = None
    image_urls: List[str] = None
    image_data: Optional[str] = None
    posted_date: str = ""

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []

    @property
    def economy(self) -> float:
        """Рассчитывает экономию"""
        return self.target_price - self.price

    @property
    def economy_percent(self) -> int:
        """Рассчитывает процент экономии"""
        if self.target_price > 0:
            return int((self.economy / self.target_price) * 100)
        return 0

    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            'name': self.name,
            'price': self.price,
            'target_price': self.target_price,
            'url': self.url,
            'category': self.category,
            'description': self.description,
            'seller_name': self.seller_name,
            'seller_rating': self.seller_rating,
            'reviews_count': self.reviews_count,
            'avito_category': self.avito_category,
            'city': self.city,
            'image_url': self.image_url,
            'image_urls': self.image_urls,
            'image_data': self.image_data,
            'posted_date': self.posted_date
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        """Создает из словаря"""
        return cls(**data)