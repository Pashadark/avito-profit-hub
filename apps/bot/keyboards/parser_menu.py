"""
Меню парсера
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_parser_menu_keyboard():
    """Меню парсера"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="parser_stats"),
         InlineKeyboardButton("🔍 Мои запросы", callback_data="parser_queries")],
        [InlineKeyboardButton("🚀 Запустить парсер", callback_data="parser_start"),
         InlineKeyboardButton("⏹️ Остановить", callback_data="parser_stop")],
        [InlineKeyboardButton("➕ Добавить запрос", callback_data="parser_add_query"),
         InlineKeyboardButton("🗑️ Очистить", callback_data="parser_clear")],
        [InlineKeyboardButton("💾 Экспорт данных", callback_data="parser_export")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_parser_stats_keyboard():
    """Клавиатура для статистики парсера"""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="parser_stats"),
         InlineKeyboardButton("📊 Детальная статистика", callback_data="parser_detailed_stats")],
        [InlineKeyboardButton("🤖 Назад к меню парсера", callback_data="menu_parser"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_parser_queries_keyboard():
    """Клавиатура для запросов парсера"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить запрос", callback_data="parser_add_query"),
         InlineKeyboardButton("🗑️ Очистить все", callback_data="parser_clear")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="parser_queries"),
         InlineKeyboardButton("🤖 Назад", callback_data="menu_parser")]
    ]
    return InlineKeyboardMarkup(keyboard)