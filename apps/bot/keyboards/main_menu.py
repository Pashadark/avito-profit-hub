"""
Главное меню бота
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard():
    """Главное меню для привязанных пользователей"""
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🤖 Парсер", callback_data="menu_parser")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")],
        [InlineKeyboardButton("📖 Справка", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_unlinked_menu_keyboard():
    """Меню для непривязанных пользователей"""
    keyboard = [
        [InlineKeyboardButton("🔗 Привязать аккаунт", callback_data="link_account")],
        [InlineKeyboardButton("🆔 Узнать мой User ID", callback_data="settings_userid")],
        [InlineKeyboardButton("📖 Справка", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_main_menu_keyboard():
    """Кнопка возврата в главное меню"""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_refresh_keyboard(callback_data):
    """Кнопка обновления"""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data=callback_data)],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)