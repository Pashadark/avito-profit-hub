"""
Меню задач
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_todo_main_keyboard():
    """Главное меню задач"""
    keyboard = [
        [InlineKeyboardButton("📝 Создать задачу", callback_data="todo_create")],
        [InlineKeyboardButton("📋 Мои задачи", callback_data="todo_list")],
        [InlineKeyboardButton("⚡ Активные", callback_data="todo_active"),
         InlineKeyboardButton("✅ Выполненные", callback_data="todo_done")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_task_management_keyboard(task_id):
    """Кнопки управления конкретной задачей"""
    keyboard = [
        [
            InlineKeyboardButton("➡️ В процесс", callback_data=f"todo_start_{task_id}"),
            InlineKeyboardButton("✅ Выполнено", callback_data=f"todo_complete_{task_id}")
        ],
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"todo_edit_{task_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"todo_delete_{task_id}")
        ],
        [InlineKeyboardButton("📋 К списку задач", callback_data="todo_list"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_task_list_keyboard():
    """Клавиатура для списка задач"""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="todo_list"),
         InlineKeyboardButton("📝 Создать", callback_data="todo_create")],
        [InlineKeyboardButton("⚡ Активные", callback_data="todo_active"),
         InlineKeyboardButton("✅ Выполненные", callback_data="todo_done")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_task_create_keyboard():
    """Клавиатура при создании задачи"""
    keyboard = [
        [InlineKeyboardButton("📋 К списку задач", callback_data="todo_list")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)