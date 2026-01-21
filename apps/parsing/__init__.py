"""
Модуль парсинга Avito ProfitHub
"""

# Ленивая загрузка парсера для избежания дублирования инициализации
_parser_instance = None

def get_selenium_parser():
    """
    Ленивая загрузка парсера (singleton)
    Создает экземпляр только при первом вызове
    """
    global _parser_instance

    if _parser_instance is None:
        from .utils.selenium_parser import SeleniumAvitoParser
        _parser_instance = SeleniumAvitoParser()

    return _parser_instance

# Для обратной совместимости
selenium_parser = get_selenium_parser()

# Экспорт для импорта
__all__ = ['SeleniumAvitoParser', 'selenium_parser', 'get_selenium_parser']