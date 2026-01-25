"""
Меню профиля пользователя
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_profile_menu_keyboard():
    """Меню профиля"""
    keyboard = [
        [InlineKeyboardButton("💰 Баланс", callback_data="profile_balance"),
         InlineKeyboardButton("🔔 Подписка", callback_data="profile_subscription")],
        [InlineKeyboardButton("📦 Мои товары", callback_data="profile_items"),
         InlineKeyboardButton("📊 Статистика", callback_data="profile_stats")],
        [InlineKeyboardButton("📋 Мои задачи", callback_data="todo_list")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_balance_keyboard():
    """Клавиатура для баланса"""
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton("🔔 Подписка", callback_data="profile_subscription")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="profile_balance"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_subscription_keyboard():
    """Клавиатура для подписки"""
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton("💰 Баланс", callback_data="profile_balance")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="profile_subscription"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_items_keyboard():
    """Клавиатура для товаров"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="profile_stats"),
         InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="profile_items"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_stats_keyboard():
    """Клавиатура для статистики"""
    keyboard = [
        [InlineKeyboardButton("📦 Товары", callback_data="profile_items"),
         InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="profile_stats"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)