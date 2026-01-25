"""
Экспорт всех клавиатур
"""

from .main_menu import (
    get_main_menu_keyboard,
    get_unlinked_menu_keyboard,
    get_back_to_main_menu_keyboard
)

from .profile_menu import (
    get_profile_menu_keyboard,
    get_balance_keyboard,
    get_subscription_keyboard,
    get_items_keyboard,
    get_stats_keyboard
)

from .parser_menu import (
    get_parser_menu_keyboard,
    get_parser_stats_keyboard,
    get_parser_queries_keyboard
)

from .settings_menu import (
    get_settings_menu_keyboard,
    get_group_settings_keyboard,
    get_notifications_keyboard
)

from .todo_menu import (
    get_todo_main_keyboard,
    get_task_management_keyboard,
    get_task_list_keyboard,
    get_task_create_keyboard
)

__all__ = [
    'get_main_menu_keyboard',
    'get_unlinked_menu_keyboard',
    'get_back_to_main_menu_keyboard',
    'get_profile_menu_keyboard',
    'get_balance_keyboard',
    'get_subscription_keyboard',
    'get_items_keyboard',
    'get_stats_keyboard',
    'get_parser_menu_keyboard',
    'get_parser_stats_keyboard',
    'get_parser_queries_keyboard',
    'get_settings_menu_keyboard',
    'get_group_settings_keyboard',
    'get_notifications_keyboard',
    'get_todo_main_keyboard',
    'get_task_management_keyboard',
    'get_task_list_keyboard',
    'get_task_create_keyboard'
]