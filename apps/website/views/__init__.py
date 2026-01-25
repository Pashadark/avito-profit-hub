"""
Модуль views разбит на логические части:
- api_views.py - API эндпоинты
- admin_views.py - административные функции
- parser_views.py - управление парсером
- user_views.py - пользовательские функции
- database_views.py - работа с базой данных
- telegram_views.py - интеграция с Telegram
- todo_views.py - Kanban доска задач
- core_views.py - основные views (dashboard, профиль и т.д.)
- export_views.py - экспорт данных
- ml_views.py - ML статистика
"""

# Импортируем все view из модулей
from .api_views import *
from .admin_views import *
from .parser_views import *
from .user_views import *
from .database_views import *
from .telegram_views import *
from .todo_views import *
from .core_views import *
from .export_views import *
from .ml_stats_views import *
from .search_views import (
    header_search_api, universal_search_api, search_view, advanced_search_view,
    table_search_api, autocomplete_api, search_filters_api, export_search_results,
    search_queries_view, toggle_search_query, delete_search_query,
    dynamic_search_api, site_search_api
)

# Дополнительно импортируем часто используемые функции
from .core_views import (
    dashboard, help_page, search_view, found_items, found_items_view,
    found_item_detail, test_database, direct_db_query, console_output,
    clear_console_view, console_update
)
from .api_views import (
    get_latest_items, system_health_api, performance_metrics_api,
    ml_stats_api, user_parser_stats_api, get_cities_list
)
from .admin_views import (
    admin_users, edit_user, delete_user, admin_dashboard_data
)
from .parser_views import (
    parser_settings_view, get_parser_status, toggle_parser,
    launch_parser_with_params, debug_settings, test_parser, test_settings,
    parser_status, force_parser_check, debug_parser_settings,
    quick_update_settings, force_reload_all_settings, fix_database,
    force_load_all_settings, get_parser_settings, force_reload_settings,
    parser_diagnostics, test_settings_api, health_parser, parser_stats_history,
)
from .user_views import (
    profile_view, update_profile, toggle_favorite, favorites_list,
    favorites_view, check_favorite, favorites_count,
    create_subscription_payment, activate_subscription,
    debug_subscription_info, debug_subscription_detailed,
    test_subscription_notifications, products_view
)
from .database_views import (
    database_stats, backup_database, list_backups, download_backup,
    delete_backup, clean_old_backups, health_database, health_backup,
    encrypt_database, decrypt_database, start_replication, stop_replication,
    replication_status
)
from .telegram_views import (
    test_bot_connection, get_telegram_status, save_telegram_settings,
    generate_telegram_code, verify_telegram_code, unlink_telegram
)
from .todo_views import (
    todo_kanban, create_todo_card_api, update_todo_card_status_api,
    delete_todo_card_api, update_todo_card_order_api, update_todo_card_api,
    get_todo_card_api, list_todo_cards_api
)
from .export_views import (
    export_found_items_to_excel, export_found_items_to_pdf,
    export_found_items_to_csv, export_found_items_universal, export_all_zip
)
from .ml_stats_views import  (
    vision_statistics, user_ml_stats_api, ml_stats_api,
    vision_stats_api, clear_vision_cache, export_vision_knowledge, health_vision,
    ml_dashboard, api_ml_stats, api_ml_test, api_ml_retrain
)

# Экспортируем все для удобного импорта
__all__ = [
    # Core views
    'dashboard',
    'help_page',
    'search_view',
    'found_items',
    'found_items_view',
    'found_item_detail',
    'export_project_structure',
    'test_database',
    'direct_db_query',
    'console_output',
    'clear_console_view',
    'console_update',

    # API views
    'get_latest_items',
    'system_health_api',
    'performance_metrics_api',
    'ml_stats_api',
    'user_parser_stats_api',
    'user_ml_stats_api',
    # Search views
    'header_search_api',
    'universal_search_api',
    'search_view',
    'advanced_search_view',
    'table_search_api',
    'autocomplete_api',
    'search_filters_api',
    'export_search_results',
    'search_queries_view',
    'toggle_search_query',
    'delete_search_query',
    'dynamic_search_api',
    'site_search_api',

    # Admin views
    'admin_users',
    'edit_user',
    'delete_user',
    'admin_dashboard_data',
    'vision_statistics',

    # Parser views
    'parser_settings_view',
    'get_parser_status',
    'toggle_parser',
    'launch_parser_with_params',
    'parser_status',
    'force_parser_check',
    'debug_settings',
    'test_parser',
    'test_settings',
    'debug_parser_settings',
    'quick_update_settings',
    'force_reload_all_settings',
    'fix_database',
    'force_load_all_settings',
    'get_parser_settings',
    'force_reload_settings',
    'parser_diagnostics',
    'test_settings_api',
    'health_parser',
    'parser_stats_history',

    # User views
    'profile_view',
    'update_profile',
    'toggle_favorite',
    'favorites_list',
    'favorites_view',
    'check_favorite',
    'favorites_count',
    'create_subscription_payment',
    'activate_subscription',
    'products_view',

    # Database views
    'database_stats',
    'backup_database',
    'list_backups',
    'download_backup',
    'delete_backup',
    'clean_old_backups',
    'health_database',
    'health_backup',
    'encrypt_database',
    'decrypt_database',
    'start_replication',
    'stop_replication',
    'replication_status',

    # Telegram views
    'test_bot_connection',
    'get_telegram_status',
    'save_telegram_settings',
    'generate_telegram_code',
    'verify_telegram_code',
    'unlink_telegram',

    # Todo views
    'todo_kanban',
    'create_todo_card_api',
    'update_todo_card_status_api',
    'delete_todo_card_api',
    'update_todo_card_order_api',
    'update_todo_card_api',
    'get_todo_card_api',
    'list_todo_cards_api',

    # Export views
    'export_found_items_to_excel',
    'export_found_items_to_pdf',
    'export_found_items_to_csv',
    'export_found_items_universal',
    'export_all_zip',

    # ML views
    'user_ml_stats_api',
    'ml_stats_api',
    'vision_stats_api',
    'clear_vision_cache',
    'export_vision_knowledge',
    'ml_dashboard',
    'api_ml_stats',
    'api_ml_test',
    'api_ml_retrain',
]