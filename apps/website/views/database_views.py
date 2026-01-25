from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from pathlib import Path
import json
import os
import shutil
import logging
import sqlite3
from datetime import datetime, timedelta

from apps.website.models import FoundItem, SearchQuery
from apps.website.console_manager import add_to_console
from apps.core.utils.backup_manager import backup_manager

logger = logging.getLogger(__name__)


# Создаем папку для бэкапов если ее нет
BACKUP_DIR = Path('database_backups')
if not BACKUP_DIR.exists():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ========== УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ ==========

@require_GET
@login_required
def database_stats(request):
    """📊 Возвращает детальную статистику базы данных PostgreSQL - РЕАЛЬНЫЕ ДАННЫЕ

    📏 Размер базы данных
    💾 Свободное место на диске
    📋 Количество таблиц и записей
    """
    try:
        from django.db import connection
        import psutil

        with connection.cursor() as cursor:
            # Размер базы данных
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size_pretty = cursor.fetchone()[0]

            cursor.execute("SELECT pg_database_size(current_database());")
            db_size_bytes = cursor.fetchone()[0]
            db_size_mb = db_size_bytes / (1024 * 1024)

            # Количество таблиц
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE';
            """)
            tables_count = cursor.fetchone()[0]

            # Общее количество записей
            cursor.execute("""
                SELECT SUM(n_live_tup) 
                FROM pg_stat_user_tables;
            """)
            total_records = cursor.fetchone()[0] or 0

            # Активные соединения
            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';")
            active_connections = cursor.fetchone()[0]

            # Время работы базы
            cursor.execute("SELECT pg_postmaster_start_time();")
            start_time = cursor.fetchone()[0]

        # Использование диска
        try:
            disk_info = psutil.disk_usage('/')
            free_space_gb = disk_info.free / (1024 ** 3)
            total_space_gb = disk_info.total / (1024 ** 3)
            disk_percent = disk_info.percent
            has_disk_info = True
        except Exception:
            free_space_gb = 0
            total_space_gb = 0
            disk_percent = 0
            has_disk_info = False

        # Статистика по таблицам (топ 5 по размеру)
        table_stats = {}
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    table_name,
                    pg_size_pretty(pg_total_relation_size('"' || table_schema || '"."' || table_name || '"')) as size,
                    (SELECT n_live_tup FROM pg_stat_user_tables WHERE relname = t.table_name) as row_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY pg_total_relation_size('"' || table_schema || '"."' || table_name || '"') DESC
                LIMIT 5;
            """)

            for row in cursor.fetchall():
                table_name, size, row_count = row
                table_stats[table_name] = {
                    'size': size,
                    'row_count': row_count or 0
                }

        response_data = {
            'status': 'success',
            'database': {
                'size': db_size_pretty,
                'size_mb': round(db_size_mb, 2),
                'tables_count': tables_count,
                'total_records': total_records,
                'active_connections': active_connections,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'
            },
            'disk': {
                'free_space_gb': round(free_space_gb, 2) if has_disk_info else 'N/A',
                'total_space_gb': round(total_space_gb, 2) if has_disk_info else 'N/A',
                'usage_percent': round(disk_percent, 2) if has_disk_info else 'N/A'
            },
            'table_stats': table_stats,
            'total_tables': tables_count
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Database stats error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения статистики: {str(e)}'
        })

def health_database(request):
    """🗄️ Проверка здоровья базы данных

    🔌 Проверяет подключение к базе
    ✅ Простой запрос SELECT 1
    """
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return JsonResponse({
                'status': 'healthy',
                'message': 'База данных работает нормально'
            })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка базы данных: {str(e)}'
        }, status=500)

def health_backup(request):
    """💾 Проверка системы бэкапов

    📁 Проверяет существование директории бэкапов
    📊 Считает количество бэкапов
    """
    try:
        import os
        backup_dir = 'backups'
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.backup')]
            return JsonResponse({
                'status': 'healthy',
                'message': f'Найдено {len(backups)} бэкапов',
                'backup_count': len(backups)
            })
        else:
            return JsonResponse({
                'status': 'warning',
                'message': 'Директория бэкапов не найдена'
            })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка системы бэкапов: {str(e)}'
        }, status=500)

# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========

@login_required
def products_view(request):
    """🔄 Совместимость со старым кодом - перенаправляем на found_items

    🔄 Редирект для поддержки старых URL
    📦 Перенаправление на основную страницу товаров
    """
    return redirect('found_items')


@login_required
def help_page(request):
    """📚 Страница помощи по структуре проекта

    ℹ️ Общая информация о системе
    📁 Структура проекта и компоненты
    """
    return render(request, 'dashboard/help.html')


def encrypt_database(request):
    """🔐 Шифрует базу данных

    🔐 ТОЛЬКО для суперпользователей
    🔒 Использование DatabaseSecurity для шифрования
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Требуются права администратора'})

    try:
        from apps.website.encryption import DatabaseSecurity

        security = DatabaseSecurity()
        if security.encrypt_database():
            return JsonResponse({'status': 'success', 'message': 'База данных зашифрована'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Ошибка шифрования'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def decrypt_database(request):
    """🔓 Расшифровывает базу данных

    🔐 ТОЛЬКО для суперпользователей
    🔓 Использование DatabaseSecurity для дешифрования
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Требуются права администратора'})

    try:
        from apps.website.encryption import DatabaseSecurity

        security = DatabaseSecurity()
        if security.decrypt_database():
            return JsonResponse({'status': 'success', 'message': 'База данных расшифрована'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Ошибка дешифрования или файл не найден'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def start_replication(request):
    """🔄 Запускает репликацию базы данных

    🔐 ТОЛЬКО для суперпользователей
    📡 Использование DatabaseReplication для репликации
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Требуются права администратора'})

    try:
        from apps.website.database_replication import DatabaseReplication

        replicator = DatabaseReplication()
        if replicator.start_replication():
            return JsonResponse({'status': 'success', 'message': 'Репликация запущена'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Репликация уже запущена'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def stop_replication(request):
    """🛑 Останавливает репликацию базы данных

    🔐 ТОЛЬКО для суперпользователей
    ⏹️ Использование DatabaseReplication для остановки репликации
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Требуются права администратора'})

    try:
        from apps.website.database_replication import DatabaseReplication

        replicator = DatabaseReplication()
        replicator.stop_replication()

        return JsonResponse({'status': 'success', 'message': 'Репликация остановлена'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def replication_status(request):
    """📡 Возвращает статус репликации

    🔍 Получение текущего статуса репликации
    📊 Информация о процессе репликации
    """
    try:
        from apps.website.database_replication import DatabaseReplication

        replicator = DatabaseReplication()
        status = replicator.get_replication_status()

        return JsonResponse({
            'status': 'success',
            'replication_status': status
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_GET
@login_required
def database_info(request):
    """ℹ️ Получение информации о базе данных PostgreSQL

    🔍 Статистика базы данных
    📊 Подсчет всех записей во всех таблицах
    ⏰ Поиск записей старше 30 дней
    """
    try:
        from ..models import FoundItem

        cutoff_date = timezone.now() - timedelta(days=30)

        with connection.cursor() as cursor:
            # Получаем размер базы
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]

            # Получаем список таблиств
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE';
            """)
            tables = [row[0] for row in cursor.fetchall()]

            # Статистика по записям старше 30 дней
            old_items_count = FoundItem.objects.filter(found_at__lt=cutoff_date).count()

            # Общее количество записей
            total_records = 0
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_records += cursor.fetchone()[0]

        return JsonResponse({
            'status': 'success',
            'database_size': db_size,
            'old_records_count': old_items_count,
            'total_records_count': total_records,
            'tables_count': len(tables),
            'tables_list': tables[:10]  # Возвращаем только первые 10 таблиц
        })

    except Exception as e:
        logger.error(f"Database info error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения информации: {str(e)}'
        })


@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def clean_database(request):
    """🧹 Очистка старых записей базы данных PostgreSQL

    ⏰ Удаление записей старше N дней
    🗑️ Очистка найденных товаров и поисковых запросов
    ⚡ Оптимизация базы с помощью VACUUM
    """
    try:
        data = json.loads(request.body)
        days_to_keep = int(data.get('days_to_keep', 30))
        clean_logs = data.get('clean_logs', True)
        clean_products = data.get('clean_products', True)

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        deleted_total = 0

        add_to_console(f"🧹 Начинаем очистку PostgreSQL. Режим: {days_to_keep} дней")

        with connection.cursor() as cursor:
            if clean_products:
                # Удаляем старые товары
                if days_to_keep == 0:  # Удалить все
                    cursor.execute("DELETE FROM website_founditem;")
                    deleted_found = cursor.rowcount
                else:
                    cursor.execute("""
                        DELETE FROM website_founditem 
                        WHERE found_at < %s;
                    """, [cutoff_date])
                    deleted_found = cursor.rowcount

                deleted_total += deleted_found
                add_to_console(f"🗑️ Удалено товаров: {deleted_found}")

            # Очищаем старые поисковые запросы без привязанных товаров
            cursor.execute("""
                DELETE FROM website_searchquery 
                WHERE id NOT IN (
                    SELECT DISTINCT search_query_id 
                    FROM website_founditem 
                    WHERE search_query_id IS NOT NULL
                );
            """)
            deleted_queries = cursor.rowcount
            deleted_total += deleted_queries
            add_to_console(f"🗑️ Удалено поисковых запросов: {deleted_queries}")

            # Оптимизируем базу
            cursor.execute("VACUUM ANALYZE;")
            add_to_console("✅ База PostgreSQL оптимизирована")

        # Получаем размер базы после очистки
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]

        return JsonResponse({
            'status': 'success',
            'deleted_total': deleted_total,
            'database_size': db_size,
            'message': f'Очистка PostgreSQL завершена! Удалено записей: {deleted_total}'
        })

    except Exception as e:
        add_to_console(f"❌ Критическая ошибка очистки PostgreSQL: {e}")
        logger.error(f"Clean database error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка очистки PostgreSQL: {str(e)}'
        })


@require_POST
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def force_clean_database(request):
    """🔥 Экстренная очистка ВСЕХ данных PostgreSQL

    🔐 ТОЛЬКО для суперпользователей
    💾 Создает резервную копию перед очисткой
    🗑️ Удаляет ВСЕ найденные товары и поисковые запросы
    ⚡ Полная очистка базы данных
    """
    try:
        # Сначала создаем резервную копию
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"postgres_emergency_backup_{timestamp}.sql"
        backup_path = BACKUP_DIR / backup_filename

        from ..utils.backup_manager import backup_manager
        backup_result = backup_manager.create_postgres_backup()

        if backup_result['status'] != 'success':
            return JsonResponse({
                'status': 'error',
                'message': f'Не удалось создать резервную копию: {backup_result.get("error", "Неизвестная ошибка")}'
            })

        # Удаляем данные
        with connection.cursor() as cursor:
            # Отключаем foreign key проверки для безопасности
            cursor.execute("SET session_replication_role = 'replica';")

            # Удаляем данные из таблиц
            cursor.execute("DELETE FROM website_founditem;")
            deleted_found = cursor.rowcount

            cursor.execute("DELETE FROM website_searchquery;")
            deleted_queries = cursor.rowcount

            # Восстанавливаем foreign key проверки
            cursor.execute("SET session_replication_role = 'origin';")

            # VACUUM для освобождения места
            cursor.execute("VACUUM ANALYZE;")

        # Получаем размер базы
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]

        deleted_total = deleted_found + deleted_queries

        add_to_console(f"🔥 Экстренная очистка PostgreSQL: удалено {deleted_total} записей")

        return JsonResponse({
            'status': 'success',
            'deleted_total': deleted_total,
            'database_size': db_size,
            'backup_file': backup_result.get('backup_path'),
            'message': f'Экстренная очистка PostgreSQL! Удалено: {deleted_total} записей. Резервная копия создана.'
        })

    except Exception as e:
        logger.error(f"Force clean error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка экстренной очистки PostgreSQL: {str(e)}'
        })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def diagnose_decimal_problems(request):
    """🔍 Расширенная диагностика проблемных Decimal значений во ВСЕЙ базе PostgreSQL

    📊 Анализ типов данных в полях price, target_price, profit
    🎯 Поиск проблемных записей с неправильными типами
    📈 Статистика проблем по всей базе
    💡 Рекомендации по исправлению
    """
    try:
        import time
        from decimal import Decimal, InvalidOperation
        from ..models import FoundItem

        start_time = time.time()

        # Статистика через PostgreSQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN price IS NULL OR price::text = '' THEN 1 END) as price_empty,
                    COUNT(CASE WHEN target_price IS NULL OR target_price::text = '' THEN 1 END) as target_price_empty,
                    COUNT(CASE WHEN profit IS NULL OR profit::text = '' THEN 1 END) as profit_empty,
                    MIN(id) as min_id,
                    MAX(id) as max_id
                FROM website_founditem
            """)

            stats = cursor.fetchone()

        total_records = stats[0]
        price_empty = stats[1]
        target_price_empty = stats[2]
        profit_empty = stats[3]
        min_id = stats[4]
        max_id = stats[5]

        # Проверяем проблемные записи
        problematic_items = FoundItem.objects.filter(
            Q(price__isnull=True) | Q(price='') |
            Q(target_price__isnull=True) | Q(target_price='') |
            Q(profit__isnull=True) | Q(profit='')
        ).order_by('id')[:50]  # Ограничиваем для производительности

        detailed_problematic = []
        for item in problematic_items:
            record_info = {
                'id': item.id,
                'title': item.title[:100] + '...' if item.title and len(item.title) > 100 else item.title,
                'problems': [],
                'raw_values': {
                    'price': str(item.price),
                    'target_price': str(item.target_price),
                    'profit': str(item.profit)
                }
            }

            # Проверяем каждое поле
            for field_name in ['price', 'target_price', 'profit']:
                value = getattr(item, field_name)
                if value is None or value == '':
                    record_info['problems'].append(f"{field_name}: пустое значение")
                else:
                    try:
                        # Пробуем преобразовать в Decimal
                        decimal_value = Decimal(str(value))
                        quantized = decimal_value.quantize(Decimal('0.01'))
                        record_info[f'{field_name}_decimal'] = float(quantized)
                    except (InvalidOperation, TypeError, ValueError) as e:
                        problem_desc = f"{field_name}: {type(e).__name__} - {str(e)}"
                        record_info['problems'].append(problem_desc)
                        record_info[f'{field_name}_error'] = str(e)

            detailed_problematic.append(record_info)

        # Получаем нормальные записи для сравнения
        normal_samples = FoundItem.objects.exclude(
            Q(price__isnull=True) | Q(price='') |
            Q(target_price__isnull=True) | Q(target_price='') |
            Q(profit__isnull=True) | Q(profit='')
        ).order_by('?')[:10].values('id', 'title', 'price', 'target_price', 'profit')

        end_time = time.time()

        report = {
            'processing_time': round(end_time - start_time, 2),
            'database_stats': {
                'total_records': total_records,
                'id_range': f"{min_id} - {max_id}",
                'price_problems': {'empty_values': price_empty, 'total': price_empty},
                'target_price_problems': {'empty_values': target_price_empty, 'total': target_price_empty},
                'profit_problems': {'empty_values': profit_empty, 'total': profit_empty},
                'total_problematic_records': problematic_items.count(),
                'problem_percentage': round((problematic_items.count() / total_records) * 100,
                                            2) if total_records > 0 else 0
            },
            'detailed_problematic': detailed_problematic,
            'normal_samples': list(normal_samples),
            'recommendation': f"Рекомендуется исправить {problematic_items.count()} проблемных записей" if problematic_items.count() > 0 else "База данных в порядке"
        }

        return JsonResponse({
            'status': 'success',
            'report': report
        })

    except Exception as e:
        import traceback
        logger.error(f"Diagnose decimal error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка диагностики: {str(e)}',
            'traceback': traceback.format_exc()
        })


@require_GET
@login_required
def check_database_stats(request):
    """📈 Проверка статистики базы данных PostgreSQL

    📊 Количество записей в основных таблицах
    🔍 Проверка существования таблиц
    📈 Общая статистика системы
    """
    try:
        from ..models import FoundItem, SearchQuery, UserProfile, ParserSettings

        with connection.cursor() as cursor:
            # Получаем статистику с помощью Django ORM
            found_items_count = FoundItem.objects.count()
            search_queries_count = SearchQuery.objects.count()

            # Для UserProfile и ParserSettings используем прямой запрос
            cursor.execute("SELECT COUNT(*) FROM website_userprofile")
            profiles_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM website_parsersettings")
            settings_count = cursor.fetchone()[0]

            # Получаем размер базы данных
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database()));
            """)
            db_size = cursor.fetchone()[0]

        return JsonResponse({
            'status': 'success',
            'stats': {
                'found_items': found_items_count,
                'search_queries': search_queries_count,
                'parser_settings': settings_count,
                'user_profiles': profiles_count,
                'total_records': found_items_count + search_queries_count + settings_count + profiles_count,
                'database_size': db_size
            },
            'message': f'Найдено товаров: {found_items_count}, Поисковых запросов: {search_queries_count}, Размер БД: {db_size}'
        })

    except Exception as e:
        logger.error(f"Database stats error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения статистики: {str(e)}'
        })


# ========== API ДЛЯ РЕЗЕРВНОГО КОПИРОВАНИЯ БАЗЫ ДАННЫХ ==========

@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def backup_database(request):
    """💾 Создание резервной копии PostgreSQL базы данных

    📁 Создает дамп PostgreSQL через pg_dump
    🕒 Добавляет timestamp в имя файла
    📏 Сжимает файл с помощью gzip
    📤 Отправляет в Telegram (если настроено)
    """
    try:
        from ..utils.backup_manager import backup_manager

        # Используем наш менеджер бэкапов
        result = backup_manager.create_postgres_backup()

        if result['status'] == 'success':
            backup_path = Path(result['backup_path'])
            backup_filename = backup_path.name

            return JsonResponse({
                'status': 'success',
                'backup_path': backup_filename,
                'file_size': f"{result['size'] / 1024:.1f} KB",
                'full_path': str(backup_path),
                'message': 'Резервная копия PostgreSQL создана успешно'
            })
        else:
            logger.error(f"Backup creation failed: {result.get('error')}")
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка создания бэкапа: {result.get("error", "Неизвестная ошибка")}'
            })

    except Exception as e:
        logger.error(f"Backup database error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка создания бэкапа PostgreSQL: {str(e)}'
        })


@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def restore_backup(request):
    """🔄 Восстановление PostgreSQL базы данных из резервной копии

    ⚠️ Создает safety backup текущей базы
    📂 Восстанавливает из указанного файла .sql.gz
    🔒 Проверяет существование файла
    """
    try:
        data = json.loads(request.body)
        filename = data.get('filename')

        if not filename:
            return JsonResponse({'status': 'error', 'message': 'Не указано имя файла'})

        backup_path = BACKUP_DIR / filename

        if not backup_path.exists():
            return JsonResponse({'status': 'error', 'message': 'Файл бэкапа не найден'})

        # Проверяем, что это PostgreSQL бэкап
        if not filename.endswith('.sql.gz'):
            return JsonResponse({
                'status': 'error',
                'message': 'Неправильный формат файла. Ожидается .sql.gz'
            })

        logger.info(f"🔄 Восстановление PostgreSQL из бэкапа: {filename}")

        # Создаем safety backup текущей базы
        safety_result = backup_manager.create_postgres_backup()
        if safety_result['status'] != 'success':
            return JsonResponse({
                'status': 'error',
                'message': f'Не удалось создать safety backup: {safety_result.get("error")}'
            })

        # Восстанавливаем через менеджер
        restore_result = backup_manager.restore_postgres_backup(filename)

        if restore_result['status'] == 'success':
            return JsonResponse({
                'status': 'success',
                'message': f'База данных PostgreSQL восстановлена из {filename}. Safety backup создан: {safety_result.get("backup_path")}',
                'safety_backup': Path(safety_result['backup_path']).name
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка восстановления: {restore_result.get("error", "Неизвестная ошибка")}'
            })

    except Exception as e:
        logger.error(f"Restore backup error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка восстановления PostgreSQL: {str(e)}'
        })


@require_GET
@login_required
def list_backups(request):
    """📋 Получение списка всех резервных копий PostgreSQL

    📁 Сканирует папку бэкапов
    📏 Показывает размер каждого файла
    🕒 Сортировка по дате создания (новые сверху)
    🔍 Фильтрация по типу бэкапа
    """
    try:
        backups = []

        if BACKUP_DIR.exists():
            # Ищем файлы PostgreSQL бэкапов
            for file in BACKUP_DIR.glob('*.sql.gz'):
                if file.is_file():
                    file_size = file.stat().st_size
                    created_time = datetime.fromtimestamp(file.stat().st_mtime)

                    # Определяем тип бэкапа по имени
                    backup_type = 'unknown'
                    if 'postgres' in file.name.lower():
                        backup_type = 'postgres'
                    elif 'vision' in file.name.lower():
                        backup_type = 'vision'
                    elif 'emergency' in file.name.lower():
                        backup_type = 'emergency'

                    backups.append({
                        'filename': file.name,
                        'size': f'{file_size / 1024:.1f} KB',
                        'size_bytes': file_size,
                        'created': created_time.strftime("%d.%m.%Y %H:%M"),
                        'created_timestamp': created_time.timestamp(),
                        'type': backup_type,
                        'is_postgres': 'postgres' in file.name.lower()
                    })

            # Сортировка по дате (новые сверху)
            backups.sort(key=lambda x: x['created_timestamp'], reverse=True)

        return JsonResponse({
            'status': 'success',
            'backups': backups,
            'total': len(backups),
            'postgres_count': len([b for b in backups if b['is_postgres']]),
            'directory': str(BACKUP_DIR.absolute())
        })

    except Exception as e:
        logger.error(f"List backups error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения списка бэкапов: {str(e)}'
        })


@require_GET
@login_required
def download_backup(request):
    """⬇️ Скачивание резервной копии PostgreSQL

    📥 Отправляет файл как attachment
    🔒 Проверяет существование файла
    📦 Отправляет сжатый .gz файл
    """
    try:
        filename = request.GET.get('filename')
        if not filename:
            return JsonResponse({'status': 'error', 'message': 'Не указано имя файла'})

        backup_path = BACKUP_DIR / filename

        if not backup_path.exists():
            return JsonResponse({'status': 'error', 'message': 'Файл не найден'})

        # Определяем Content-Type
        if filename.endswith('.gz'):
            content_type = 'application/gzip'
        elif filename.endswith('.sql'):
            content_type = 'application/sql'
        else:
            content_type = 'application/octet-stream'

        response = FileResponse(open(backup_path, 'rb'))
        response['Content-Type'] = content_type
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = backup_path.stat().st_size

        # Дополнительные заголовки для безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        logger.info(f"📥 Скачивание бэкапа: {filename} ({backup_path.stat().st_size / 1024:.1f} KB)")
        return response

    except Exception as e:
        logger.error(f"Download backup error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка скачивания: {str(e)}'
        })


@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_backup(request):
    """🗑️ Удаление конкретной резервной копии PostgreSQL

    🔐 ТОЛЬКО для суперпользователей
    🔒 Проверяет существование файла
    📝 Логирует операцию
    """
    try:
        data = json.loads(request.body)
        filename = data.get('filename')

        if not filename:
            return JsonResponse({'status': 'error', 'message': 'Не указано имя файла'})

        backup_path = BACKUP_DIR / filename

        if not backup_path.exists():
            return JsonResponse({'status': 'error', 'message': 'Файл не найден'})

        # Получаем информацию о файле перед удалением
        file_size = backup_path.stat().st_size
        created_time = datetime.fromtimestamp(backup_path.stat().st_mtime)

        # Удаляем файл
        backup_path.unlink()

        logger.info(f"🗑️ Удален бэкап PostgreSQL: {filename} ({file_size / 1024:.1f} KB)")
        add_to_console(f"🗑️ Удален бэкап: {filename}")

        return JsonResponse({
            'status': 'success',
            'message': f'Бэкап PostgreSQL {filename} удален',
            'deleted_file': {
                'filename': filename,
                'size_kb': round(file_size / 1024, 2),
                'created': created_time.strftime("%d.%m.%Y %H:%M")
            }
        })

    except Exception as e:
        logger.error(f"Delete backup error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка удаления: {str(e)}'
        })


@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def clean_old_backups(request):
    """🧹 Очистка старых резервных копий PostgreSQL (старше 30 дней)

    ⏰ Удаляет файлы старше указанного количества дней
    📊 Возвращает количество удаленных файлов
    ⚙️ Можно указать кастомное количество дней
    """
    try:
        data = json.loads(request.body) if request.body else {}
        days_to_keep = int(data.get('days', 30))

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        deleted_files = []

        if BACKUP_DIR.exists():
            for file in BACKUP_DIR.glob('*.sql.gz'):
                if file.is_file():
                    created_time = datetime.fromtimestamp(file.stat().st_mtime)

                    if created_time < cutoff_date:
                        try:
                            file_size = file.stat().st_size
                            file.unlink()
                            deleted_count += 1
                            deleted_files.append({
                                'filename': file.name,
                                'size_kb': file_size / 1024,
                                'created': created_time.strftime("%d.%m.%Y")
                            })
                        except Exception as e:
                            logger.error(f"Error deleting {file.name}: {e}")
                            continue

        add_to_console(f"🧹 Очистка PostgreSQL бэкапов: удалено {deleted_count} файлов старше {days_to_keep} дней")

        return JsonResponse({
            'status': 'success',
            'deleted_count': deleted_count,
            'days_to_keep': days_to_keep,
            'deleted_files': deleted_files,
            'message': f'Удалено {deleted_count} старых PostgreSQL бэкапов (старше {days_to_keep} дней)'
        })

    except Exception as e:
        logger.error(f"Clean old backups error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка очистки бэкапов: {str(e)}'
        })


@require_POST
@csrf_exempt
def backup_vision_database(request):
    """💾 Создание бэкапа vision_knowledge.db

    📁 Копирует базу данных Vision AI
    🕒 Добавляет timestamp
    📏 Возвращает размер файла
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"vision_backup_{timestamp}.db"
        backup_path = BACKUP_DIR / backup_filename

        shutil.copy2('vision_knowledge.db', backup_path)

        file_size = os.path.getsize(backup_path)
        size_mb = round(file_size / (1024 * 1024), 2)

        return JsonResponse({
            'status': 'success',
            'backup_path': backup_filename,
            'file_size': f'{size_mb} MB',
            'message': 'Vision AI database backup created successfully'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Vision backup error: {str(e)}'
        })