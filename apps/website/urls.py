# website/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views

# Импортируем ВСЁ из папки views (через __init__.py)
from .views import (
    # Все функции из views.py
    dashboard, products_view, found_items_view, profile_view, user_settings,
    save_telegram_settings, add_from_telegram, search_queries_view,
    toggle_search_query, delete_search_query, parser_settings_view, toggle_parser,
    force_parser_check, debug_settings, todo_kanban, help_page, recalculate_balance,
    create_subscription_payment, ajax_save_settings, start_parser_with_settings,
    launch_parser_with_params, get_parser_status, debug_parser_settings,
    found_item_detail, ml_stats_api, get_latest_items, vision_statistics,
    vision_stats_api, clear_vision_cache, export_vision_knowledge,
    favorites_list, toggle_favorite, check_favorite, favorites_count,
    parser_statistics, parser_stats_api, reset_parser_stats, export_parser_data,
    test_subscription_notifications, admin_users, edit_user, delete_user,
    toggle_user_status, register_start, register_view, confirm_registration,
    parser_diagnostics, health_parser, health_database, health_backup,
    health_vision, admin_logs_api, system_health_api, performance_metrics_api,
    create_todo_card_api, get_todo_card_api, update_todo_card_api,
    update_todo_card_status_api, delete_todo_card_api, list_todo_cards_api,
    update_todo_card_order_api, test_database, test_settings, direct_db_query,
    get_parser_settings, fix_database, activate_subscription,
    force_load_all_settings, force_reload_all_settings, force_reload_settings,
    generate_telegram_code, verify_telegram_code, get_telegram_status,
    unlink_telegram, test_bot_connection, debug_subscription_info,
    debug_subscription_detailed, parser_stats_history, update_profile,
    change_password, clear_avatar, console_output, clear_console_view,
    console_update, clean_database, database_info, database_stats,
    backup_database, list_backups, restore_backup, download_backup,
    delete_backup, clean_old_backups, quick_update_settings,
    check_database_stats, force_clean_database, test_settings_api,
    encrypt_database, decrypt_database, start_replication,
    stop_replication, replication_status, dynamic_search_api, site_search_api,
    user_parser_stats_api, user_ml_stats_api, export_project_structure,

    # Функции из search.py тоже должны импортироваться через __init__.py
    universal_search_api, header_search_api, table_search_api,
    autocomplete_api, search_filters_api, export_search_results,
    search_view, advanced_search_view,

    # Функции экспорта
    export_found_items_to_excel, export_found_items_to_pdf, export_found_items_to_csv,
    export_found_items_universal, export_all_zip, ml_dashboard, api_ml_stats, api_ml_test, api_ml_retrain
)

# Теперь функции из search.py доступны напрямую
# Переименуем если есть конфликт
search_view_search = search_view
advanced_search_view_search = advanced_search_view

# ВАЖНО: Добавьте это для работы namespace
app_name = 'website'

urlpatterns = [
    # -------------------- ГЛАВНЫЕ СТРАНИЦЫ --------------------
    path('', dashboard, name='dashboard'),
    path('products/', products_view, name='products'),
    path('found-items/', found_items_view, name='found_items'),
    path('profile/', profile_view, name='profile'),
    path('user-settings/', user_settings, name='user_settings'),

    # -------------------- ПОИСК --------------------
    path('search/', search_view_search, name='search'),
    path('search/advanced/', advanced_search_view_search, name='advanced_search'),

    # -------------------- API ПОИСКА --------------------
    path('api/search/universal/', universal_search_api, name='universal_search_api'),
    path('api/search/header/', header_search_api, name='header_search_api'),
    path('api/search/table/', table_search_api, name='table_search_api'),
    path('api/search/autocomplete/', autocomplete_api, name='autocomplete_api'),
    path('api/search/filters/', search_filters_api, name='search_filters_api'),
    path('api/search/export/', export_search_results, name='export_search_results'),
    path('api/search/dynamic/', dynamic_search_api, name='dynamic_search_api'),
    path('api/search/site/', site_search_api, name='site_search_api'),
    path('export-project-structure/', export_project_structure, name='export_project_structure'),

    # -------------------- ЭКСПОРТ ТОВАРОВ --------------------
    path('export/all-zip/', export_all_zip, name='export_all_zip'),
    path('found-items/export/excel/', export_found_items_to_excel, name='export_excel'),
    path('found-items/export/pdf/', export_found_items_to_pdf, name='export_pdf'),
    path('found-items/export/csv/', export_found_items_to_csv, name='export_csv'),
    path('found-items/export/universal/', export_found_items_universal, name='export_universal'),

    # -------------------- ПОИСКОВЫЕ ЗАПРОСЫ --------------------
    path('search-queries/', search_queries_view, name='search_queries'),
    path('search-queries/toggle/<int:query_id>/', toggle_search_query, name='toggle_search_query'),
    path('search-queries/delete/<int:query_id>/', delete_search_query, name='delete_search_query'),

    # -------------------- TELEGRAM --------------------
    path('add-from-telegram/', add_from_telegram, name='add_from_telegram'),
    path('save-telegram-settings/', save_telegram_settings, name='save_telegram_settings'),

    # -------------------- ПАРСЕР --------------------
    path('toggle-parser/', toggle_parser, name='toggle_parser'),
    path('launch-parser-with-params/', launch_parser_with_params, name='launch_parser_with_params'),
    path('api/parser-status/', get_parser_status, name='parser_status'),
    path('parser-settings/', parser_settings_view, name='parser_settings'),
    path('parser-settings/toggle/', toggle_parser, name='toggle_parser'),
    path('parser-settings/force-check/', force_parser_check, name='force_parser_check'),
    path('start-parser-with-settings/', start_parser_with_settings, name='start_parser_with_settings'),
    path('launch-parser-with-params/', launch_parser_with_params, name='launch_parser_with_params'),
    path('api/parser-status/', get_parser_status, name='parser_status'),
    path('api/debug-parser-settings/', debug_parser_settings, name='debug_parser_settings'),
    path('api/user-parser-stats/', user_parser_stats_api, name='user_parser_stats_api'),
    path('api/user-ml-stats/', user_ml_stats_api, name='user_ml_stats_api'),

    # -------------------- ML СТАТИСТИКА --------------------
    path('ml-stats/', ml_dashboard, name='ml_stats'),
    path('api/ml-stats/', api_ml_stats, name='api_ml_stats'),
    path('api/ml-test/', api_ml_test, name='api_ml_test'),
    path('api/ml-retrain/', api_ml_retrain, name='api_ml_retrain'),

    # -------------------- ОТЛАДКА --------------------
    path('debug-settings/', debug_settings, name='debug_settings'),
    path('parser-diagnostics/', parser_diagnostics, name='parser_diagnostics'),

    # -------------------- ЗАДАЧИ (TODO) --------------------
    path('todo/', todo_kanban, name='todo_kanban'),

    # -------------------- ПОМОЩЬ --------------------
    path('help/', help_page, name='help'),

    # -------------------- ПРОФИЛЬ И БАЛАНС --------------------
    path('profile/recalculate-balance/', recalculate_balance, name='recalculate_balance'),
    path('profile/update/', update_profile, name='update_profile'),
    path('profile/change-password/', change_password, name='change_password'),
    path('profile/clear-avatar/', clear_avatar, name='clear_avatar'),

    # -------------------- ПОДПИСКИ И ПЛАТЕЖИ --------------------
    path('api/create-subscription-payment/', create_subscription_payment, name='create_subscription_payment'),
    path('api/activate-subscription/', activate_subscription, name='activate_subscription'),

    # -------------------- AJAX И НАСТРОЙКИ --------------------
    path('ajax-save-settings/', ajax_save_settings, name='ajax_save_settings'),
    path('quick-update-settings/', quick_update_settings, name='quick_update_settings'),

    # -------------------- ТОВАРЫ --------------------
    path('found-items/<int:item_id>/', found_item_detail, name='found_item_detail'),

    # -------------------- ML СТАТИСТИКА --------------------
    path('api/ml-stats/', ml_stats_api, name='ml_stats_api'),
    path('api/latest-items/', get_latest_items, name='latest_items_api'),

    # -------------------- VISION AI --------------------
    path('vision-statistics/', vision_statistics, name='vision_statistics'),
    path('api/vision-stats/', vision_stats_api, name='vision_stats_api'),
    path('api/vision-cache/clear/', clear_vision_cache, name='clear_vision_cache'),
    path('api/vision-knowledge/export/', export_vision_knowledge, name='export_vision_knowledge'),

    # -------------------- ИЗБРАННОЕ --------------------
    path('favorites/', favorites_list, name='favorites'),
    path('favorites/toggle/<int:item_id>/', toggle_favorite, name='toggle_favorite'),
    path('favorites/check/<int:item_id>/', check_favorite, name='check_favorite'),
    path('favorites/count/', favorites_count, name='favorites_count'),

    # -------------------- СТАТИСТИКА ПАРСЕРА --------------------
    path('statistics/parser/', parser_statistics, name='parser_statistics'),
    path('api/parser-stats/', parser_stats_api, name='parser_stats_api'),
    path('api/reset-parser-stats/', reset_parser_stats, name='reset_parser_stats'),
    path('api/parser-data/export/', export_parser_data, name='export_parser_data'),
    path('api/parser-stats-history/', parser_stats_history, name='parser_stats_history'),

    # -------------------- УВЕДОМЛЕНИЯ --------------------
    path('api/test-subscription-notifications/', test_subscription_notifications,
         name='test_subscription_notifications'),

    # -------------------- АДМИНИСТРИРОВАНИЕ ПОЛЬЗОВАТЕЛЕЙ --------------------
    path('admin-users/', admin_users, name='admin_users'),
    path('admin-users/edit/<int:user_id>/', edit_user, name='edit_user'),
    path('admin-users/delete/<int:user_id>/', delete_user, name='delete_user'),
    path('admin-users/toggle-status/<int:user_id>/', toggle_user_status, name='toggle_user_status'),

    # -------------------- АУТЕНТИФИКАЦИЯ --------------------
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', register_start, name='register'),
    path('register/form/', register_view, name='register_form'),
    path('confirm/', confirm_registration, name='confirm_registration'),

    # -------------------- HEALTH CHECKS --------------------
    path('api/health/parser/', health_parser, name='health_parser'),
    path('api/health/database/', health_database, name='health_database'),
    path('api/health/backup/', health_backup, name='health_backup'),
    path('api/health/vision/', health_vision, name='health_vision'),
    path('api/admin-logs/', admin_logs_api, name='admin_logs_api'),
    path('api/system-health/', system_health_api, name='system_health_api'),
    path('api/performance-metrics/', performance_metrics_api, name='performance_metrics_api'),

    # -------------------- API ДЛЯ ЗАДАЧ (TODO) --------------------
    path('api/todo/create/', create_todo_card_api, name='create_todo_card'),
    path('api/todo/get/<int:card_id>/', get_todo_card_api, name='get_todo_card'),
    path('api/todo/update/<int:card_id>/', update_todo_card_api, name='update_todo_card'),
    path('api/todo/update-status/<int:card_id>/', update_todo_card_status_api, name='update_todo_status'),
    path('api/todo/delete/<int:card_id>/', delete_todo_card_api, name='delete_todo_card'),
    path('api/todo/list/', list_todo_cards_api, name='list_todo_cards'),
    path('api/todo/update-order/', update_todo_card_order_api, name='update_todo_order'),

    # -------------------- ОТЛАДКА И ТЕСТИРОВАНИЕ --------------------
    path('api/test-database/', test_database, name='test_database'),
    path('api/test-settings/', test_settings, name='test_settings'),
    path('api/direct-db-query/', direct_db_query, name='direct_db_query'),
    path('api/get-parser-settings/', get_parser_settings, name='get_parser_settings'),
    path('api/fix-database/', fix_database, name='fix_database'),

    # -------------------- УПРАВЛЕНИЕ НАСТРОЙКАМИ --------------------
    path('api/force-load-all-settings/', force_load_all_settings, name='force_load_all_settings'),
    path('api/force-reload-all-settings/', force_reload_all_settings, name='force_reload_all_settings'),
    path('api/force-reload-settings/', force_reload_settings, name='force_reload_settings'),

    # -------------------- TELEGRAM API --------------------
    path('api/telegram/generate-code/', generate_telegram_code, name='generate_telegram_code'),
    path('api/telegram/verify-code/', verify_telegram_code, name='verify_telegram_code'),
    path('api/telegram/status/', get_telegram_status, name='get_telegram_status'),
    path('api/telegram/unlink/', unlink_telegram, name='unlink_telegram'),
    path('api/test-bot-connection/', test_bot_connection, name='test_bot_connection'),

    # -------------------- ОТЛАДКА ПОДПИСОК --------------------
    path('api/debug-subscription/', debug_subscription_info, name='debug_subscription'),
    path('api/debug-subscription-detailed/', debug_subscription_detailed, name='debug_subscription_detailed'),

    # -------------------- КОНСОЛЬ --------------------
    path('api/console-output/', console_output, name='console_output'),
    path('api/clear-console/', clear_console_view, name='clear_console'),
    path('api/console-update/', console_update, name='console_update'),

    # -------------------- БАЗА ДАННЫХ И БЭКАПЫ --------------------
    path('api/clean-database/', clean_database, name='clean_database'),
    path('api/database-info/', database_info, name='database_info'),
    path('api/database-stats/', database_stats, name='database_stats'),
    path('api/backup-database/', backup_database, name='backup_database'),
    path('api/list-backups/', list_backups, name='list_backups'),
    path('api/restore-backup/', restore_backup, name='restore_backup'),
    path('api/download-backup/', download_backup, name='download_backup'),
    path('api/delete-backup/', delete_backup, name='delete_backup'),
    path('api/clean-old-backups/', clean_old_backups, name='clean_old_backups'),

    # -------------------- ДОПОЛНИТЕЛЬНЫЕ API ДЛЯ ОТЛАДКИ --------------------
    path('api/check-db-stats/', check_database_stats, name='check_db_stats'),
    path('api/force-clean-database/', force_clean_database, name='force_clean_database'),
    path('api/test-settings-api/', test_settings_api, name='test_settings_api'),

    # -------------------- БЕЗОПАСНОСТЬ --------------------
    path('api/encrypt-database/', encrypt_database, name='encrypt_database'),
    path('api/decrypt-database/', decrypt_database, name='decrypt_database'),

    # -------------------- РЕПЛИКАЦИЯ --------------------
    path('api/start-replication/', start_replication, name='start_replication'),
    path('api/stop-replication/', stop_replication, name='stop_replication'),
    path('api/replication-status/', replication_status, name='replication_status'),
]