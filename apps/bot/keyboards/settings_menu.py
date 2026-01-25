"""
Меню настроек
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_settings_menu_keyboard():
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton("🆔 User ID", callback_data="settings_userid")],
        [InlineKeyboardButton("👥 Управление группой", callback_data="settings_group")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications")],
        [InlineKeyboardButton("🔗 Привязка аккаунта", callback_data="link_account")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_group_settings_keyboard():
    """Настройки группы"""
    keyboard = [
        [InlineKeyboardButton("ℹ️ Информация о группе", callback_data="group_info")],
        [InlineKeyboardButton("👥 Участники", callback_data="group_members"),
         InlineKeyboardButton("⚙️ Настройки лимитов", callback_data="group_limits")],
        [InlineKeyboardButton("⚙️ Назад к настройкам", callback_data="menu_settings"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notifications_keyboard():
    """Настройки уведомлений"""
    keyboard = [
        [InlineKeyboardButton("🔔 Включить уведомления", callback_data="notifications_on"),
         InlineKeyboardButton("🔕 Выключить уведомления", callback_data="notifications_off")],
        [InlineKeyboardButton("⚙️ Назад к настройкам", callback_data="menu_settings"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)