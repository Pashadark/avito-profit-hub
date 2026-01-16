"""
Core package initialization
"""

try:
    from .logging_config import setup_logging
    # Инициализируем систему логирования при загрузке Django
    setup_logging()
except ImportError as e:
    print(f"⚠️ Не удалось импортировать logging_config: {e}")
except Exception as e:
    print(f"⚠️ Ошибка инициализации логирования: {e}")

__all__ = ()