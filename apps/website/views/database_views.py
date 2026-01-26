from django.shortcuts import render, redirect
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
from datetime import datetime, timedelta
import psutil
import subprocess
import gzip

from apps.website.models import FoundItem, SearchQuery, UserProfile, ParserSettings
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
    """📊 Возвращает детальную статистику базы данных PostgreSQL - РЕАЛЬНЫЕ ДАННЫХ

    📏 Размер базы данных
    💾 Свободное место на диске
    📋 Количество таблиц и записей
    """
    try:
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

            # Получаем список баз данных на сервере
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
            databases = [row[0] for row in cursor.fetchall()]

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
                    (SELECT n_live_tup FROM pg_stat_user_tables WHERE relname = t.table_name) as row_count,
                    pg_size_pretty(pg_relation_size('"' || table_schema || '"."' || table_name || '"')) as table_size,
                    pg_size_pretty(pg_total_relation_size('"' || table_schema || '"."' || table_name || '"') - pg_relation_size('"' || table_schema || '"."' || table_name || '"')) as indexes_size
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY pg_total_relation_size('"' || table_schema || '"."' || table_name || '"') DESC
                LIMIT 10;
            """)

            for row in cursor.fetchall():
                table_name, size, row_count, table_size, indexes_size = row
                table_stats[table_name] = {
                    'total_size': size,
                    'row_count': row_count or 0,
                    'table_size': table_size,
                    'indexes_size': indexes_size or '0 bytes'
                }

        # ФИКС: Правильное вычисление uptime
        uptime_str = 'N/A'
        if start_time:
            try:
                # Преобразуем start_time в наивный datetime если он offset-aware
                if start_time.tzinfo is not None:
                    # Если время с часовым поясом, конвертируем в наивное (местное)
                    start_time_naive = start_time.replace(tzinfo=None)
                else:
                    start_time_naive = start_time

                # Используем timezone.now() для осведомленного времени
                from django.utils import timezone
                now_aware = timezone.now()

                # Если start_time_naive тоже нужно сделать осведомленным
                # Предположим, что start_time_naive в том же часовом поясе, что и now_aware
                import pytz
                from django.conf import settings

                # Получаем текущий часовой пояс Django
                try:
                    current_tz = timezone.get_current_timezone()
                    start_time_aware = current_tz.localize(start_time_naive)
                except:
                    # Если не удалось, используем UTC
                    start_time_aware = start_time_naive.replace(tzinfo=pytz.UTC)

                # Вычисляем разницу
                uptime = now_aware - start_time_aware

                # Форматируем uptime
                days = uptime.days
                hours, remainder = divmod(uptime.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                if days > 0:
                    uptime_str = f"{days}d {hours}h {minutes}m"
                else:
                    uptime_str = f"{hours}h {minutes}m {seconds}s"

            except Exception as e:
                logger.warning(f"Could not calculate uptime: {e}")
                # Альтернативный расчет без учета часовых поясов
                try:
                    from datetime import datetime
                    now_naive = datetime.now()
                    uptime = now_naive - start_time_naive
                    uptime_str = str(uptime).split('.')[0]
                except:
                    uptime_str = 'N/A'

        response_data = {
            'status': 'success',
            'database': {
                'name': connection.settings_dict['NAME'],
                'size': db_size_pretty,
                'size_mb': round(db_size_mb, 2),
                'tables_count': tables_count,
                'total_records': total_records,
                'active_connections': active_connections,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A',
                'uptime': uptime_str,
                'host': connection.settings_dict.get('HOST', 'localhost'),
                'port': connection.settings_dict.get('PORT', 5432),
                'available_databases': databases
            },
            'disk': {
                'free_space_gb': round(free_space_gb, 2) if has_disk_info else 'N/A',
                'total_space_gb': round(total_space_gb, 2) if has_disk_info else 'N/A',
                'usage_percent': round(disk_percent, 2) if has_disk_info else 'N/A',
                'free_percent': round(100 - disk_percent, 2) if has_disk_info else 'N/A'
            },
            'table_stats': table_stats,
            'total_tables': tables_count
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Database stats error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения статистики: {str(e)}'
        })


@require_GET
@login_required
def health_database(request):
    """🗄️ Проверка здоровья базы данных PostgreSQL

    🔌 Проверяет подключение к базе
    ✅ Простой запрос SELECT 1
    📊 Проверка доступности
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            # Дополнительные проверки
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]

            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity;")
            connections = cursor.fetchone()[0]

        return JsonResponse({
            'status': 'healthy',
            'message': 'База данных PostgreSQL работает нормально',
            'details': {
                'database': db_name,
                'postgres_version': version,
                'active_connections': connections,
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка базы данных: {str(e)}'
        }, status=500)


@require_GET
@login_required
def health_backup(request):
    """💾 Проверка системы бэкапов PostgreSQL

    📁 Проверяет существование директории бэкапов
    📊 Считает количество бэкапов
    💽 Проверяет доступность pg_dump
    """
    try:
        backup_dir = BACKUP_DIR

        # Проверяем доступность pg_dump
        try:
            result = subprocess.run(['pg_dump', '--version'],
                                    capture_output=True, text=True, timeout=5)
            pg_dump_available = result.returncode == 0
        except:
            pg_dump_available = False

        if backup_dir.exists():
            # Ищем PostgreSQL бэкапы
            backups = []
            for ext in ['.sql', '.sql.gz']:
                backups.extend(list(backup_dir.glob(f'*{ext}')))

            backup_count = len(backups)
            latest_backup = max(backups, key=lambda x: x.stat().st_mtime) if backups else None

            return JsonResponse({
                'status': 'healthy',
                'message': f'Найдено {backup_count} бэкапов PostgreSQL',
                'details': {
                    'backup_count': backup_count,
                    'backup_dir': str(backup_dir),
                    'pg_dump_available': pg_dump_available,
                    'latest_backup': latest_backup.name if latest_backup else None,
                    'latest_backup_size': f"{latest_backup.stat().st_size / 1024:.1f} KB" if latest_backup else None,
                    'latest_backup_age':
                        str(datetime.now() - datetime.fromtimestamp(latest_backup.stat().st_mtime)).split('.')[
                            0] if latest_backup else None
                }
            })
        else:
            return JsonResponse({
                'status': 'warning',
                'message': 'Директория бэкапов не найдена',
                'details': {
                    'pg_dump_available': pg_dump_available,
                    'suggestion': 'Создайте директорию database_backups/'
                }
            })
    except Exception as e:
        logger.error(f"Backup health check failed: {e}")
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


@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def start_replication(request):
    """🔄 Запускает репликацию базы данных PostgreSQL

    🔐 ТОЛЬКО для суперпользователей
    📡 Использование DatabaseReplication для репликации
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Требуются права администратора'})

    try:
        from apps.website.database_replication import DatabaseReplication

        # Получаем конфигурацию базы данных
        from django.conf import settings
        db_config = settings.DATABASES['default']

        # Создаем конфигурацию для репликатора
        primary_config = {
            'dbname': db_config['NAME'],
            'user': db_config['USER'],
            'password': db_config['PASSWORD'],
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', '5432')
        }

        replicator = DatabaseReplication(primary_config)
        if replicator.start_replication():
            return JsonResponse({
                'status': 'success',
                'message': 'Репликация PostgreSQL запущена'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Репликация уже запущена или не удалось запустить'
            })
    except Exception as e:
        logger.error(f"Start replication error: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def stop_replication(request):
    """🛑 Останавливает репликацию базы данных PostgreSQL

    🔐 ТОЛЬКО для суперпользователей
    ⏹️ Использование DatabaseReplication для остановки репликации
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Требуются права администратора'})

    try:
        from apps.website.database_replication import DatabaseReplication

        # Получаем конфигурацию базы данных
        from django.conf import settings
        db_config = settings.DATABASES['default']

        primary_config = {
            'dbname': db_config['NAME'],
            'user': db_config['USER'],
            'password': db_config['PASSWORD'],
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', '5432')
        }

        replicator = DatabaseReplication(primary_config)
        replicator.stop_replication()

        return JsonResponse({
            'status': 'success',
            'message': 'Репликация PostgreSQL остановлена'
        })
    except Exception as e:
        logger.error(f"Stop replication error: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_GET
@login_required
def replication_status(request):
    """📡 Возвращает статус репликации PostgreSQL

    🔍 Получение текущего статуса репликации
    📊 Информация о процессе репликации
    """
    try:
        from apps.website.database_replication import DatabaseReplication

        from django.conf import settings
        db_config = settings.DATABASES['default']

        primary_config = {
            'dbname': db_config['NAME'],
            'user': db_config['USER'],
            'password': db_config['PASSWORD'],
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', '5432')
        }

        replicator = DatabaseReplication(primary_config)
        status = replicator.get_replication_status()

        return JsonResponse({
            'status': 'success',
            'replication_status': status
        })
    except Exception as e:
        logger.error(f"Replication status error: {e}", exc_info=True)
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
        cutoff_date = timezone.now() - timedelta(days=30)

        with connection.cursor() as cursor:
            # Получаем размер базы
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]

            # Получаем список таблиц
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]

            # Статистика по записям старше 30 дней
            old_items_count = FoundItem.objects.filter(found_at__lt=cutoff_date).count()

            # Общее количество записей
            total_records = 0
            table_counts = {}
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
                table_counts[table] = count
                total_records += count

        return JsonResponse({
            'status': 'success',
            'database_size': db_size,
            'old_records_count': old_items_count,
            'total_records_count': total_records,
            'tables_count': len(tables),
            'tables_list': tables[:20],  # Возвращаем первые 20 таблиц
            'table_counts': table_counts
        })

    except Exception as e:
        logger.error(f"Database info error: {e}", exc_info=True)
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
                    cursor.execute('DELETE FROM "website_founditem";')
                    deleted_found = cursor.rowcount
                else:
                    cursor.execute("""
                        DELETE FROM "website_founditem" 
                        WHERE found_at < %s;
                    """, [cutoff_date])
                    deleted_found = cursor.rowcount

                deleted_total += deleted_found
                add_to_console(f"🗑️ Удалено товаров: {deleted_found}")

            # Очищаем старые поисковые запросы без привязанных товаров
            cursor.execute("""
                DELETE FROM "website_searchquery" 
                WHERE id NOT IN (
                    SELECT DISTINCT search_query_id 
                    FROM "website_founditem" 
                    WHERE search_query_id IS NOT NULL
                );
            """)
            deleted_queries = cursor.rowcount
            deleted_total += deleted_queries
            add_to_console(f"🗑️ Удалено поисковых запросов: {deleted_queries}")

            # Оптимизируем базу (VACUUM в PostgreSQL работает иначе)
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
        logger.error(f"Clean database error: {e}", exc_info=True)
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

        from ..utils.backup_manager import backup_manager
        backup_result = backup_manager.create_postgres_backup(backup_name=f"emergency_backup_{timestamp}")

        if backup_result['status'] != 'success':
            return JsonResponse({
                'status': 'error',
                'message': f'Не удалось создать резервную копию: {backup_result.get("error", "Неизвестная ошибка")}'
            })

        # Удаляем данные
        with connection.cursor() as cursor:
            # Отключаем foreign key проверки для безопасности
            cursor.execute("SET session_replication_role = 'replica';")

            # Удаляем данные из таблиц в правильном порядке
            tables_to_clean = [
                'website_founditem',
                'website_searchquery',
                'website_todocard',
                'website_todoboard',
                'website_trackedproduct',
                'website_userprofile',
                'website_parsersettings'
            ]

            deleted_total = 0
            for table in tables_to_clean:
                try:
                    cursor.execute(f'DELETE FROM "{table}";')
                    deleted = cursor.rowcount
                    deleted_total += deleted
                    logger.info(f"Deleted {deleted} rows from {table}")
                except Exception as e:
                    logger.warning(f"Could not clean table {table}: {e}")

            # Восстанавливаем foreign key проверки
            cursor.execute("SET session_replication_role = 'origin';")

            # VACUUM для освобождения места
            cursor.execute("VACUUM ANALYZE;")

        # Получаем размер базы
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]

        add_to_console(f"🔥 Экстренная очистка PostgreSQL: удалено {deleted_total} записей")

        return JsonResponse({
            'status': 'success',
            'deleted_total': deleted_total,
            'database_size': db_size,
            'backup_file': backup_result.get('backup_path'),
            'message': f'Экстренная очистка PostgreSQL! Удалено: {deleted_total} записей. Резервная копия создана.'
        })

    except Exception as e:
        logger.error(f"Force clean error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка экстренной очистки PostgreSQL: {str(e)}'
        })


@require_GET
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
                FROM "website_founditem"
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
        logger.error(f"Diagnose decimal error: {e}", exc_info=True)
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
        with connection.cursor() as cursor:
            # Получаем статистику с помощью Django ORM
            found_items_count = FoundItem.objects.count()
            search_queries_count = SearchQuery.objects.count()
            profiles_count = UserProfile.objects.count()
            settings_count = ParserSettings.objects.count()

            # Получаем размер базы данных
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database()));
            """)
            db_size = cursor.fetchone()[0]

            # Получаем информацию о сервере
            cursor.execute("SELECT version();")
            postgres_version = cursor.fetchone()[0]

        return JsonResponse({
            'status': 'success',
            'stats': {
                'found_items': found_items_count,
                'search_queries': search_queries_count,
                'parser_settings': settings_count,
                'user_profiles': profiles_count,
                'total_records': found_items_count + search_queries_count + settings_count + profiles_count,
                'database_size': db_size,
                'postgres_version': postgres_version.split(',')[0] if postgres_version else 'Unknown'
            },
            'message': f'Найдено товаров: {found_items_count}, Поисковых запросов: {search_queries_count}, Размер БД: {db_size}'
        })

    except Exception as e:
        logger.error(f"Database stats error: {e}", exc_info=True)
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
                'file_size': f"{result['size'] / (1024 * 1024):.2f} MB" if result[
                                                                               'size'] > 1024 * 1024 else f"{result['size'] / 1024:.1f} KB",
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
        logger.error(f"Backup database error: {e}", exc_info=True)
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
        if not (filename.endswith('.sql.gz') or filename.endswith('.sql')):
            return JsonResponse({
                'status': 'error',
                'message': 'Неправильный формат файла. Ожидается .sql или .sql.gz'
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
        logger.error(f"Restore backup error: {e}", exc_info=True)
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
            for pattern in ['*.sql.gz', '*.sql']:
                for file in BACKUP_DIR.glob(pattern):
                    if file.is_file():
                        file_size = file.stat().st_size
                        created_time = datetime.fromtimestamp(file.stat().st_mtime)

                        # Определяем тип бэкапа по имени
                        backup_type = 'unknown'
                        filename_lower = file.name.lower()

                        if 'postgres' in filename_lower or 'backup' in filename_lower:
                            backup_type = 'postgres'
                        elif 'vision' in filename_lower:
                            backup_type = 'vision'
                        elif 'emergency' in filename_lower:
                            backup_type = 'emergency'
                        elif 'schema' in filename_lower:
                            backup_type = 'schema'

                        backups.append({
                            'filename': file.name,
                            'size': f'{file_size / (1024 * 1024):.2f} MB' if file_size > 1024 * 1024 else f'{file_size / 1024:.1f} KB',
                            'size_bytes': file_size,
                            'created': created_time.strftime("%d.%m.%Y %H:%M"),
                            'created_timestamp': created_time.timestamp(),
                            'type': backup_type,
                            'is_postgres': backup_type == 'postgres',
                            'is_compressed': file.name.endswith('.gz')
                        })

            # Сортировка по дате (новые сверху)
            backups.sort(key=lambda x: x['created_timestamp'], reverse=True)

        return JsonResponse({
            'status': 'success',
            'backups': backups,
            'total': len(backups),
            'postgres_count': len([b for b in backups if b['is_postgres']]),
            'total_size_mb': round(sum(b['size_bytes'] for b in backups) / (1024 * 1024), 2),
            'directory': str(BACKUP_DIR.absolute())
        })

    except Exception as e:
        logger.error(f"List backups error: {e}", exc_info=True)
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
    📦 Отправляет сжатый .gz файл или .sql
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
        response['X-Frame-Options'] = 'DENY'

        logger.info(f"📥 Скачивание бэкапа PostgreSQL: {filename} ({backup_path.stat().st_size / (1024 * 1024):.2f} MB)")
        return response

    except Exception as e:
        logger.error(f"Download backup error: {e}", exc_info=True)
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

        logger.info(f"🗑️ Удален бэкап PostgreSQL: {filename} ({file_size / (1024 * 1024):.2f} MB)")
        add_to_console(f"🗑️ Удален бэкап PostgreSQL: {filename}")

        return JsonResponse({
            'status': 'success',
            'message': f'Бэкап PostgreSQL {filename} удален',
            'deleted_file': {
                'filename': filename,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'created': created_time.strftime("%d.%m.%Y %H:%M")
            }
        })

    except Exception as e:
        logger.error(f"Delete backup error: {e}", exc_info=True)
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
        total_freed_bytes = 0

        if BACKUP_DIR.exists():
            for pattern in ['*.sql.gz', '*.sql']:
                for file in BACKUP_DIR.glob(pattern):
                    if file.is_file():
                        created_time = datetime.fromtimestamp(file.stat().st_mtime)

                        if created_time < cutoff_date:
                            try:
                                file_size = file.stat().st_size
                                file.unlink()
                                deleted_count += 1
                                total_freed_bytes += file_size
                                deleted_files.append({
                                    'filename': file.name,
                                    'size_mb': round(file_size / (1024 * 1024), 2),
                                    'created': created_time.strftime("%d.%m.%Y")
                                })
                            except Exception as e:
                                logger.error(f"Error deleting {file.name}: {e}")
                                continue

        total_freed_mb = round(total_freed_bytes / (1024 * 1024), 2)
        add_to_console(
            f"🧹 Очистка PostgreSQL бэкапов: удалено {deleted_count} файлов старше {days_to_keep} дней, освобождено {total_freed_mb} MB")

        return JsonResponse({
            'status': 'success',
            'deleted_count': deleted_count,
            'days_to_keep': days_to_keep,
            'deleted_files': deleted_files,
            'freed_space_mb': total_freed_mb,
            'message': f'Удалено {deleted_count} старых PostgreSQL бэкапов (старше {days_to_keep} дней), освобождено {total_freed_mb} MB'
        })

    except Exception as e:
        logger.error(f"Clean old backups error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка очистки бэкапов: {str(e)}'
        })
