class SiteRegistry:
    """Реестр парсеров для разных сайтов"""

    _parsers = {}

    @classmethod
    def register_parser(cls, domain, parser_class):
        """Регистрирует парсер для домена"""
        cls._parsers[domain] = parser_class

    @classmethod
    def get_parser(cls, domain, driver):
        """Возвращает парсер для домена"""
        if domain in cls._parsers:
            return cls._parsers[domain](driver)
        return None

    @classmethod
    def get_supported_sites(cls):
        """Возвращает список поддерживаемых сайтов"""
        return list(cls._parsers.keys())


# Регистрируем парсеры
from .avito_parser import AvitoParser

SiteRegistry.register_parser('avito.ru', AvitoParser)