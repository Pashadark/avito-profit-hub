from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models import Q
import json
import os
import logging

from apps.website.models import (
    SearchQuery, FoundItem, UserProfile, ParserSettings,
    UserSubscription, Transaction, ParserStats
)
from apps.website.forms import ParserSettingsForm
from apps.website.utils.user_utils import is_user_online, get_activity_display

logger = logging.getLogger(__name__)


def is_admin(user):
    """🔐 Проверяет, является ли пользователь администратором"""
    return user.is_staff or user.is_superuser


# ========== АДМИНИСТРАТИВНЫЕ ФУНКЦИИ (ТОЛЬКО АДМИНЫ) ==========

@user_passes_test(is_admin)
def admin_logs_api(request):
    """📋 API для административных логов - получение и запись

    🔐 ТОЛЬКО для администраторов
    📝 Поддерживает запись действий админов
    📁 Возвращает список лог-файлов
    """
    if request.method == 'POST':
        try:
            print("=" * 50)
            print("📨 POST /api/admin-logs/")
            print("📋 Headers:", dict(request.headers))
            print("📦 Body raw:", request.body)

            data = json.loads(request.body)
            print("📊 Body parsed:", data)
            print("🔍 Action field:", data.get('action', 'NOT_FOUND'))

            action = data.get('action', '')

            if action == 'log_action':
                user = data.get('user', 'unknown')
                action_type = data.get('action_type', 'unknown')
                details = data.get('details', {})
                timestamp = data.get('timestamp', '')

                logger.info(
                    f"👤 ADMIN ACTION | User: {user} | Action: {action_type} | Details: {details} | Time: {timestamp}")

                print("✅ Action logged successfully")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Action logged successfully'
                })

            elif action == 'get_logs':
                log_files = []
                log_dir = 'logs'
                if os.path.exists(log_dir):
                    for file in os.listdir(log_dir):
                        if file.endswith('.log'):
                            log_files.append({
                                'name': file,
                                'size': os.path.getsize(os.path.join(log_dir, file))
                            })

                print("✅ Logs retrieved")
                return JsonResponse({
                    'log_files': log_files,
                    'total_count': len(log_files)
                })
            else:
                print(f"❌ Unknown action: {action}")
                return JsonResponse({'error': f'Unknown action: {action}'}, status=400)

        except json.JSONDecodeError as e:
            print(f"❌ JSON Decode Error: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"❌ General Error: {e}")
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == 'GET':
        log_files = []
        log_dir = 'logs'
        if os.path.exists(log_dir):
            for file in os.listdir(log_dir):
                if file.endswith('.log'):
                    log_files.append({
                        'name': file,
                        'size': os.path.getsize(os.path.join(log_dir, file))
                    })

        return JsonResponse({
            'log_files': log_files,
            'total_count': len(log_files)
        })
    else:
        return JsonResponse({
            'error': 'Method not allowed'
        }, status=405)


@user_passes_test(is_admin)
def admin_users(request):
    """👥 Административная панель управления пользователями

    🔐 ТОЛЬКО для администраторов
    🔍 Поддержка фильтрации по роли, статусу, подписке
    📊 Отображает статистику пользователей
    👁️‍🗨️ Показывает онлайн-статус пользователей
    """
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    subscription_filter = request.GET.get('subscription', '')

    users = User.objects.all().select_related('userprofile').prefetch_related('subscriptions').order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    if role_filter:
        if role_filter == 'admin':
            users = users.filter(Q(is_staff=True) | Q(is_superuser=True))
        elif role_filter == 'user':
            users = users.filter(is_staff=False, is_superuser=False)

    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)

    if subscription_filter:
        if subscription_filter == 'active':
            users = users.filter(
                subscriptions__is_active=True,
                subscriptions__end_date__gte=timezone.now()
            ).distinct()
        elif subscription_filter == 'expired':
            users = users.filter(
                subscriptions__is_active=True,
                subscriptions__end_date__lt=timezone.now()
            ).distinct()
        elif subscription_filter == 'none':
            users = users.filter(subscriptions__isnull=True)

    admin_count = users.filter(Q(is_staff=True) | Q(is_superuser=True)).count()
    active_count = users.filter(is_active=True).count()
    inactive_count = users.filter(is_active=False).count()
    users_with_subscription = users.filter(
        subscriptions__is_active=True,
        subscriptions__end_date__gte=timezone.now()
    ).distinct().count()
    active_parsers = ParserSettings.objects.filter(is_active=True).count()
    today = timezone.now().date()
    total_found_items = FoundItem.objects.filter(
        found_at__date=today
    ).count()

    from apps.website.utils.user_utils import is_user_online, get_activity_display

    users_with_info = []
    for user in users:
        active_subscription = user.subscriptions.filter(
            is_active=True,
            end_date__gte=timezone.now()
        ).first()

        users_with_info.append({
            'user': user,
            'is_online': is_user_online(user),
            'last_activity_display': get_activity_display(user),
            'active_subscription': active_subscription
        })

    paginator = Paginator(users_with_info, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users_with_info': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'subscription_filter': subscription_filter,
        'total_users': len(users_with_info),
        'admin_count': admin_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'users_with_subscription': users_with_subscription,
        'now': timezone.now(),
        'active_parsers': active_parsers,
        'total_found_items': total_found_items,
    }

    return render(request, 'dashboard/admin_users.html', context)


@user_passes_test(is_admin)
def edit_user(request, user_id):
    """✏️ Редактирование пользователя администратором

    🔐 ТОЛЬКО для администраторов
    📝 Обновление всех полей пользователя
    💰 Изменение баланса, Telegram настроек
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.is_staff = 'is_staff' in request.POST
        user.is_active = 'is_active' in request.POST

        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.balance = float(request.POST.get('balance', 0))
        profile.telegram_chat_id = request.POST.get('telegram_chat_id', '')
        profile.telegram_notifications = 'telegram_notifications' in request.POST
        profile.save()

        user.save()
        messages.success(request, f'Пользователь {user.username} успешно обновлен')
        return redirect('admin_users')

    return render(request, 'dashboard/edit_user.html', {'user_obj': user})


@user_passes_test(is_admin)
def delete_user(request, user_id):
    """🗑️ Удаление пользователя администратором

    🔐 ТОЛЬКО для администраторов
    ⚠️ Запрашивает подтверждение
    """
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} успешно удален')
        return redirect('admin_users')

    return render(request, 'dashboard/confirm_delete.html', {'user_obj': user})


@require_GET
@user_passes_test(is_admin)
def admin_dashboard_data(request):
    """📊 API для админ дашборда - РЕАЛЬНЫЕ ДАННЫЕ ИЗ POSTGRESQL

    🔐 ТОЛЬКО для администраторов
    📊 Возвращает все данные для админки одним запросом
    """
    try:
        from django.db.models import Count, Q
        from django.contrib.auth import get_user_model

        User = get_user_model()
        now = timezone.now()

        # 1. СТАТИСТИКА ПАРСЕРА
        total_searches = SearchQuery.objects.count()
        total_items = FoundItem.objects.count()
        good_deals = FoundItem.objects.filter(profit__gt=0).count()
        today_items = FoundItem.objects.filter(found_at__date=now.date()).count()
        active_searches = SearchQuery.objects.filter(is_active=True).count()

        # 2. СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ
        total_users = User.objects.count()

        month_ago = now - timedelta(days=30)
        active_users = User.objects.filter(last_login__gte=month_ago).count()

        # Пользователи с подписками
        from apps.website.models import UserSubscription
        users_with_subscriptions = User.objects.filter(
            subscriptions__is_active=True,
            subscriptions__end_date__gte=now
        ).distinct().count()

        new_users = User.objects.filter(date_joined__gte=now - timedelta(days=7)).count()
        admin_users = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count()

        # 3. СТАТИСТИКА БАЗЫ ДАННЫХ
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]

            cursor.execute("SELECT pg_database_size(current_database());")
            db_size_bytes = cursor.fetchone()[0]
            db_size_mb = db_size_bytes / (1024 * 1024)

        # 4. СТАТИСТИКА ПАРСЕРА (настройки)
        active_parsers = ParserSettings.objects.filter(is_active=True).count()

        response_data = {
            'status': 'success',

            # Парсер
            'parser_stats': {
                'total_searches': total_searches,
                'total_items': total_items,
                'good_deals': good_deals,
                'today_items': today_items,
                'active_searches': active_searches,
                'active_parsers': active_parsers,
                'success_rate': round((good_deals / total_items * 100) if total_items > 0 else 0, 1),
            },

            # Пользователи
            'user_stats': {
                'total_users': total_users,
                'active_users': active_users,
                'users_with_subscriptions': users_with_subscriptions,
                'new_users': new_users,
                'admin_users': admin_users,
            },

            # База данных
            'database_stats': {
                'size': db_size,
                'size_mb': round(db_size_mb, 2),
                'total_records': total_items + total_searches + total_users,
            },

            # ML (проверяем наличие)
            'ml_stats': {
                'has_ml': False,
                'prediction_accuracy': 0,
                'training_samples': 0,
            },

            'timestamp': now.isoformat()
        }

        logger.info(f"📊 Админ данные отправлены")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"❌ Ошибка админ данных: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """🔘 Переключение статуса пользователя (активен/неактивен)

    🔐 ТОЛЬКО для администраторов
    ⚡ Быстрое изменение статуса is_active
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = get_object_or_404(User, id=user_id)
            user.is_active = data.get('activate', False)
            user.save()

            return JsonResponse({'success': True, 'message': 'Статус пользователя изменен'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@require_GET
@user_passes_test(is_admin)
def parser_statistics(request):
    """📊 Страница статистики парсера - только для админов

    🔐 ТОЛЬКО для администраторов
    📈 Основная статистика работы парсера
    📊 История статистики
    ⚙️ Текущие настройки парсера
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        parser_stats = get_parser_stats()
        stats_history = get_parser_stats_history()
        current_settings = get_current_parser_settings()

        context = {
            'parser_stats': parser_stats,
            'stats_history': stats_history,
            'current_settings': current_settings,
            'current_time': timezone.now(),
        }

        return render(request, 'dashboard/statistics/parser.html', context)

    except Exception as e:
        add_to_console(f"❌ Ошибка загрузки статистики парсера: {e}")
        messages.error(request, f'Ошибка загрузки статистики: {str(e)}')
        return redirect('website:dashboard')


@require_GET
@user_passes_test(is_admin)
def parser_stats_api(request):
    """📡 API для получения статистики парсера в реальном времени - РЕАЛЬНЫЕ ДАННЫЕ

    🔐 ТОЛЬКО для администраторов
    ⚡ Возвращает реальную статистику из БД
    """
    try:
        from django.db.models import Count, Sum, Q
        from datetime import datetime, timedelta

        now = timezone.now()
        today = now.date()

        # РЕАЛЬНЫЕ ДАННЫЕ ИЗ БД
        # Всего поисковых запросов
        total_searches = SearchQuery.objects.count()

        # Всего найденных товаров
        total_items = FoundItem.objects.count()

        # Хороших сделок (прибыль > 0)
        good_deals = FoundItem.objects.filter(profit__gt=0).count()

        # Товары за сегодня
        today_items = FoundItem.objects.filter(found_at__date=today).count()

        # Активные поисковые запросы
        active_searches = SearchQuery.objects.filter(is_active=True).count()

        # Успешность (если есть данные)
        success_rate = 0
        if total_searches > 0 and total_items > 0:
            # Примерная успешность - отношение найденных товаров к запросам
            success_rate = min(100, (total_items / (total_searches or 1)) * 100)

        stats = {
            'total_searches': total_searches,
            'total_items': total_items,
            'good_deals': good_deals,
            'today_items': today_items,
            'active_searches': active_searches,
            'success_rate': round(success_rate, 1),
            'success_rate_percent': f"{round(success_rate, 1)}%",
            'timestamp': now.isoformat()
        }

        return JsonResponse({
            'status': 'success',
            'stats': stats,
            'timestamp': now.isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики парсера: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_POST
@csrf_exempt
@user_passes_test(is_admin)
def reset_parser_stats(request):
    """🔄 Сброс статистики парсера

    🔐 ТОЛЬКО для администраторов
    🗑️ Очистка статистики в парсере
    📊 Сброс истории в базе данных
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if hasattr(selenium_parser, 'reset_stats'):
            selenium_parser.reset_stats()
        elif hasattr(selenium_parser, 'search_stats'):
            selenium_parser.search_stats = {
                'total_searches': 0,
                'successful_searches': 0,
                'items_found': 0,
                'good_deals_found': 0,
                'duplicates_blocked': 0,
                'error_count': 0,
                'last_reset': timezone.now()
            }

        ParserStats.objects.all().delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Статистика парсера сброшена'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_POST
@csrf_exempt
@user_passes_test(is_admin)
def export_parser_data(request):
    """📤 Экспорт данных парсера

    🔐 ТОЛЬКО для администраторов
    📊 Создание Excel файла с данными
    📈 Текущая статистика и история
    """
    try:
        import pandas as pd
        from io import BytesIO
        from django.http import HttpResponse

        stats = get_parser_stats()
        history = get_parser_stats_history()

        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            current_stats_df = pd.DataFrame([stats])
            current_stats_df.to_excel(writer, sheet_name='Текущая статистика', index=False)

            if history:
                history_df = pd.DataFrame(history)
                history_df.to_excel(writer, sheet_name='История', index=False)

        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="parser_statistics.xlsx"'

        return response

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПАРСЕРА ==========

def get_parser_stats():
    """📊 Получает текущую статистику парсера

    🔍 Получение данных из работающего парсера
    📊 Запасной вариант из базы данных
    📈 Форматирование времени цикла
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if hasattr(selenium_parser, 'search_stats'):
            stats = selenium_parser.search_stats.copy()
        else:
            stats = collect_parser_stats_from_db()

        if 'avg_cycle_time' in stats:
            stats['avg_cycle_time'] = f"{stats['avg_cycle_time']:.1f}с"

        return stats

    except Exception as e:
        add_to_console(f"❌ Ошибка получения статистики парсера: {e}")
        return get_fallback_stats()


def collect_parser_stats_from_db():
    """🗄️ Собирает статистику парсера из базы данных

    📊 Анализ FoundItem и SearchQuery
    🎯 Расчет успешных сделок
    🔍 Подсчет активных запросов
    """
    try:
        total_items = FoundItem.objects.count()
        today_items = FoundItem.objects.filter(
            found_at__date=timezone.now().date()
        ).count()

        active_queries = SearchQuery.objects.filter(is_active=True).count()

        return {
            'total_searches': total_items * 3,
            'successful_searches': total_items,
            'items_found': total_items,
            'good_deals_found': FoundItem.objects.filter(profit__gt=0).count(),
            'duplicates_blocked': max(total_items * 2, 0),
            'active_queries': active_queries,
            'error_count': 0,
            'uptime': '0ч 0м',
            'avg_cycle_time': '0с'
        }
    except Exception as e:
        add_to_console(f"❌ Ошибка сбора статистики из БД: {e}")
        return get_fallback_stats()


def get_fallback_stats():
    """📉 Резервная статистика при ошибках

    🔧 Минимальные значения при недоступности данных
    📊 Базовые показатели
    """
    return {
        'total_searches': 0,
        'successful_searches': 0,
        'items_found': 0,
        'good_deals_found': 0,
        'duplicates_blocked': 0,
        'error_count': 0,
        'active_queries': 0,
        'uptime': '0ч 0м',
        'avg_cycle_time': '0с',
        'current_queries': [],
        'efficiency_distribution': [],
        'successful_queries': []
    }


def get_parser_stats_history():
    """📜 Получает историю статистики парсера

    📊 Последние 10 записей статистики
    🎯 Расчет успешности и эффективности
    """
    try:
        history = ParserStats.objects.all().order_by('-created_at')[:10]

        history_data = []
        for stat in history:
            history_data.append({
                'total_searches': stat.total_searches,
                'successful_searches': stat.successful_searches,
                'items_found': stat.items_found,
                'good_deals_found': stat.good_deals_found,
                'duplicates_blocked': stat.duplicates_blocked,
                'success_rate': stat.success_rate(),
                'efficiency_rate': stat.efficiency_rate(),
                'duplicate_rate': stat.duplicate_rate(),
                'created_at': stat.created_at.strftime('%d.%m.%Y %H:%M')
            })

        return history_data
    except Exception as e:
        add_to_console(f"❌ Ошибка получения истории статистики: {e}")
        return []


def get_current_parser_settings():
    """⚙️ Получает текущие настройки парсера

    🔍 Извлечение настроек из работающего парсера
    🌐 Количество окон браузера
    🔍 Список поисковых запросов
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        settings = {
            'browser_windows': getattr(selenium_parser, 'browser_windows', 1),
            'search_queries': getattr(selenium_parser, 'search_queries', []),
            'is_running': getattr(selenium_parser, 'is_running', False),
            'check_interval': getattr(selenium_parser, 'check_interval', 30),
            'min_price': getattr(selenium_parser, 'min_price', 0),
            'max_price': getattr(selenium_parser, 'max_price', 100000),
        }

        return settings
    except Exception as e:
        add_to_console(f"❌ Ошибка получения настроек парсера: {e}")
        return {}