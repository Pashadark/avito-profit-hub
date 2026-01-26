from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum
from django.contrib.auth import update_session_auth_hash
from datetime import timedelta
import json
import os
import logging

from apps.website.models import (
    SearchQuery, FoundItem, UserProfile, UserSubscription,
    Transaction, SubscriptionPlan
)
from apps.website.forms import CustomUserCreationForm

logger = logging.getLogger(__name__)


# ========== НАЙДЕННЫЕ ТОВАРЫ ==========

@login_required
def found_items(request):
    """📦 Просмотр найденных товаров с поддержкой избранного

    🔍 Фильтрация по категории, цене, типу продавца, состоянию, городу, метро, новизне
    💰 Сортировка по прибыли, цене, дате
    ⭐ Режим избранного (только is_favorite=True)
    📊 Статистика: общее количество, выгодные сделки, потенциальная прибыль
    📤 Экспорт в Excel
    """
    # 📤 Экспорт в Excel
    if request.GET.get('export') == 'excel':
        from apps.website.utils.excel_export import ExcelExporterPRO
        found_items_list = FoundItem.objects.filter(
            search_query__user=request.user
        ).select_related('search_query')
        exporter = ExcelExporterPRO(found_items_list)
        return exporter.export()

    # 🔍 Определяем режим избранного
    is_favorites_view = request.GET.get('favorites') == '1'

    # 📋 Получаем базовый QuerySet (ВСЕ товары пользователя) - ЭТО КРИТИЧЕСКИ ВАЖНО!
    # ⚠️ Убедитесь, что у пользователя действительно есть товары!
    all_items_qs = FoundItem.objects.filter(
        search_query__user=request.user
    ).select_related('search_query')

    # Получаем общее количество ВСЕХ товаров пользователя (для кнопки "Все объявления")
    total_all_items = all_items_qs.count()

    # ⭐ ФИЛЬТР ИЗБРАННОГО - ПЕРВОЕ И ВАЖНЕЙШЕЕ
    if is_favorites_view:
        found_items_list = all_items_qs.filter(is_favorite=True)
        logger.info(f"⭐ Режим избранного: найдено {found_items_list.count()} товаров")
    else:
        found_items_list = all_items_qs

    # 🔍 ВСЕ ФИЛЬТРЫ ИЗ GET-ПАРАМЕТРОВ
    category_filter = request.GET.get('category')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    seller_type = request.GET.get('seller_type')
    profitable_only = request.GET.get('profitable_only')
    sort_by = request.GET.get('sort_by', '-found_at')

    # 🔥 НОВЫЕ ФИЛЬТРЫ ДЛЯ МОДАЛЬНОГО ОКНА
    condition_filter = request.GET.get('condition')
    city_filter = request.GET.get('city')
    metro_filter = request.GET.get('metro')
    newness_filter = request.GET.get('newness')

    # 📦 Фильтр по категории
    if category_filter and category_filter != 'all':
        found_items_list = found_items_list.filter(category__icontains=category_filter)

    # 💰 Фильтр по цене
    if price_min:
        try:
            found_items_list = found_items_list.filter(price__gte=float(price_min))
        except ValueError:
            pass

    if price_max:
        try:
            found_items_list = found_items_list.filter(price__lte=float(price_max))
        except ValueError:
            pass

    # 👤 Фильтр по типу продавца - СОВМЕСТИМОСТЬ со старыми и новыми данными
    if seller_type:
        if seller_type == 'private':
            # Частные лица: или reviews_count <= 150, или seller_type содержит "част"
            found_items_list = found_items_list.filter(
                Q(reviews_count__lte=150) |
                Q(seller_type__icontains='част') |
                Q(seller_type__icontains='private') |
                Q(seller_type='')
            )
        elif seller_type == 'reseller':
            # Компании/магазины: или reviews_count > 150, или seller_type содержит "компания", "магазин"
            found_items_list = found_items_list.filter(
                Q(reviews_count__gt=150) |
                Q(seller_type__icontains='компания') |
                Q(seller_type__icontains='магазин') |
                Q(seller_type__icontains='reseller') |
                Q(seller_type='Компания') |
                Q(seller_type='Магазин')
            )

    # 💵 Фильтр выгодных предложений
    if profitable_only:
        found_items_list = found_items_list.filter(profit__gt=0)

    # 🔥 НОВЫЙ ФИЛЬТР: Состояние товара
    if condition_filter:
        if condition_filter == 'new':
            found_items_list = found_items_list.filter(
                Q(condition__icontains='новый') |
                Q(condition__icontains='new')
            )
        elif condition_filter == 'used':
            found_items_list = found_items_list.filter(
                Q(condition__icontains='б/у') |
                Q(condition__icontains='used')
            )
        elif condition_filter == 'like_new':
            found_items_list = found_items_list.filter(
                Q(condition__icontains='как новый') |
                Q(condition__icontains='like new')
            )

    # 🔥 НОВЫЙ ФИЛЬТР: Город
    if city_filter:
        found_items_list = found_items_list.filter(
            Q(city__icontains=city_filter) |
            Q(full_location__icontains=city_filter)
        )

    # 🔥 НОВЫЙ ФИЛЬТР: Метро
    if metro_filter:
        found_items_list = found_items_list.filter(
            Q(metro_stations__icontains=metro_filter) |
            Q(full_location__icontains=metro_filter)
        )

    # 🔥 НОВЫЙ ФИЛЬТР: Новизна объявления
    if newness_filter:
        now = timezone.now()
        if newness_filter == 'today':
            found_items_list = found_items_list.filter(found_at__date=now.date())
        elif newness_filter == 'week':
            week_ago = now - timedelta(days=7)
            found_items_list = found_items_list.filter(found_at__gte=week_ago)
        elif newness_filter == 'month':
            month_ago = now - timedelta(days=30)
            found_items_list = found_items_list.filter(found_at__gte=month_ago)

    # 🔄 Сортировка
    if sort_by in ['price', '-price', 'category', '-category', 'posted_date', '-posted_date', '-found_at', '-profit']:
        found_items_list = found_items_list.order_by(sort_by)
    else:
        found_items_list = found_items_list.order_by('-found_at')

    # 📚 Категории для фильтра (только уникальные)
    categories = FoundItem.objects.filter(
        search_query__user=request.user
    ).exclude(category__isnull=True).exclude(category='').values_list('category', flat=True).distinct()

    # 📊 Пагинация с поддержкой размера страницы
    page_size = int(request.GET.get('page_size', 20))
    paginator = Paginator(found_items_list, page_size)
    page_number = request.GET.get('page')

    try:
        found_items = paginator.page(page_number)
    except PageNotAnInteger:
        found_items = paginator.page(1)
    except EmptyPage:
        found_items = paginator.page(paginator.num_pages)

    # 📈 Статистика для текущих отфильтрованных товаров
    total_filtered_items = found_items_list.count()
    good_deals = found_items_list.filter(profit__gt=0).count()
    potential_profit = found_items_list.aggregate(total_profit=Sum('profit'))['total_profit'] or 0

    # ❤️ Количество избранных (ВСЕХ товаров пользователя)
    favorites_count = FoundItem.objects.filter(
        search_query__user=request.user,
        is_favorite=True
    ).count()

    # 📊 ОТЛАДКА ДЛЯ ВЫЯВЛЕНИЯ ПРОБЛЕМЫ
    import sys
    print("\n" + "=" * 80, file=sys.stderr)
    print("🔍 ДЕБАГ ИНФОРМАЦИЯ found_items VIEW:", file=sys.stderr)
    print(f"  Пользователь: {request.user} (id: {request.user.id})", file=sys.stderr)
    print(f"  is_favorites_view: {is_favorites_view}", file=sys.stderr)
    print(f"  total_all_items (все товары): {total_all_items}", file=sys.stderr)
    print(f"  favorites_count (все избранные): {favorites_count}", file=sys.stderr)
    print(f"  total_filtered_items (после фильтров): {total_filtered_items}", file=sys.stderr)
    print(f"  found_items.paginator.count: {found_items.paginator.count}", file=sys.stderr)

    # Проверяем, действительно ли у пользователя есть товары
    from django.db import connection
    print("\n🔍 SQL запросы:", file=sys.stderr)
    print(f"  SQL all_items_qs: {all_items_qs.query}", file=sys.stderr)
    print(f"  Количество записей в БД для пользователя:", file=sys.stderr)

    # Проверяем количество товаров прямо в БД
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM website_founditem fi 
            JOIN website_searchquery sq ON fi.search_query_id = sq.id 
            WHERE sq.user_id = %s
        """, [request.user.id])
        db_count = cursor.fetchone()[0]
        print(f"  Прямой запрос к БД: {db_count} товаров", file=sys.stderr)

    print("=" * 80 + "\n", file=sys.stderr)

    context = {
        'found_items': found_items,
        'categories': categories,
        'current_filters': {
            'category': category_filter,
            'price_min': price_min,
            'price_max': price_max,
            'seller_type': seller_type,
            'profitable_only': profitable_only,
            'sort_by': sort_by,
            'condition': condition_filter,
            'city': city_filter,
            'metro': metro_filter,
            'newness': newness_filter,
        },
        'stats': {
            'total_items': total_filtered_items,  # Количество отфильтрованных товаров
            'good_deals': good_deals,
            'potential_profit': int(potential_profit)
        },
        'is_favorites_view': is_favorites_view,
        'favorites_count': favorites_count,
        'total_all_items': total_all_items,  # ✅ НОВОЕ: Общее количество всех товаров пользователя
        'page_size': page_size,
    }

    logger.info(f"📊 Контекст отправлен в шаблон:")
    logger.info(f"  - is_favorites_view: {is_favorites_view}")
    logger.info(f"  - favorites_count: {favorites_count}")
    logger.info(f"  - total_filtered_items: {total_filtered_items}")
    logger.info(f"  - total_all_items: {total_all_items}")
    logger.info(f"  - found_items count: {found_items.paginator.count}")

    return render(request, 'dashboard/found_items.html', context)


@login_required
def found_items_view(request):
    """📦 Просмотр найденных товаров с пагинацией, фильтрацией и сортировкой

    🔍 Альтернативная версия с экспортом в Excel
    📊 Идентичная фильтрация как в found_items()
    📤 Экспорт с применением всех фильтров
    """
    # 🔍 Определяем режим избранного - ДОБАВЛЕНО
    is_favorites_view = request.GET.get('favorites') == '1'

    # 🔧 ПОЛУЧАЕМ РАЗМЕР СТРАНИЦЫ ИЗ ЗАПРОСА - ИСПРАВЛЕНИЕ
    page_size_param = request.GET.get('page_size', '20')
    try:
        page_size = int(page_size_param)
        # Ограничиваем допустимые значения
        if page_size not in [20, 50, 100]:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20

    if request.GET.get('export') == 'excel':
        from apps.website.utils.excel_export import ExcelExporterPRO

        found_items_list = FoundItem.objects.filter(
            search_query__user=request.user
        ).select_related('search_query')

        # ⭐ ФИЛЬТР ИЗБРАННОГО ДЛЯ ЭКСПОРТА - ДОБАВЛЕНО
        if is_favorites_view:
            found_items_list = found_items_list.filter(is_favorite=True)

        category_filter = request.GET.get('category')
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')
        seller_type = request.GET.get('seller_type')
        profitable_only = request.GET.get('profitable_only')
        sort_by = request.GET.get('sort_by', '-found_at')

        if category_filter and category_filter != 'all':
            found_items_list = found_items_list.filter(category__icontains=category_filter)

        if price_min:
            try:
                found_items_list = found_items_list.filter(price__gte=float(price_min))
            except ValueError:
                pass

        if price_max:
            try:
                found_items_list = found_items_list.filter(price__lte=float(price_max))
            except ValueError:
                pass

        if seller_type == 'private':
            found_items_list = found_items_list.filter(reviews_count__lte=150)
        elif seller_type == 'reseller':
            found_items_list = found_items_list.filter(reviews_count__gt=150)

        if profitable_only:
            found_items_list = found_items_list.filter(profit__gt=0)

        if sort_by in ['price', '-price', 'category', '-category', 'posted_date', '-posted_date', '-found_at']:
            found_items_list = found_items_list.order_by(sort_by)
        else:
            found_items_list = found_items_list.order_by('-priority_score', '-ml_freshness_score', '-found_at')

        exporter = ExcelExporterPRO(found_items_list)
        return exporter.export()

    # 🔍 НАЧАЛО ФИЛЬТРАЦИИ
    found_items_list = FoundItem.objects.filter(
        search_query__user=request.user
    ).select_related('search_query')

    # ⭐ ФИЛЬТР ИЗБРАННОГО - САМОЕ ВАЖНОЕ - ДОБАВЛЕНО
    if is_favorites_view:
        found_items_list = found_items_list.filter(is_favorite=True)

    # 🔥 ДЕБАГ ИНФОРМАЦИЯ - ДОБАВЛЕНО
    print(f"🔥 DEBUG found_items_view:")
    print(f"  - is_favorites_view: {is_favorites_view}")
    print(f"  - page_size: {page_size}")
    print(f"  - request.GET: {dict(request.GET)}")
    print(f"  - Всего товаров до других фильтров: {found_items_list.count()}")

    # ... существующий код логирования ...
    from apps.website.console_manager import add_to_console
    add_to_console(f"🔍 Пользователь: {request.user}")
    add_to_console(f"🔍 Найдено записей: {found_items_list.count()}")

    # ... ОСТАЛЬНЫЕ ФИЛЬТРЫ (оставляем как было) ...
    category_filter = request.GET.get('category')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    seller_type = request.GET.get('seller_type')
    profitable_only = request.GET.get('profitable_only')
    sort_by = request.GET.get('sort_by', '-found_at')

    if category_filter and category_filter != 'all':
        found_items_list = found_items_list.filter(category__icontains=category_filter)

    if price_min:
        try:
            found_items_list = found_items_list.filter(price__gte=float(price_min))
        except ValueError:
            pass

    if price_max:
        try:
            found_items_list = found_items_list.filter(price__lte=float(price_max))
        except ValueError:
            pass

    if seller_type == 'private':
        found_items_list = found_items_list.filter(reviews_count__lte=150)
    elif seller_type == 'reseller':
        found_items_list = found_items_list.filter(reviews_count__gt=150)

    if profitable_only:
        found_items_list = found_items_list.filter(profit__gt=0)

    if sort_by in ['price', '-price', 'category', '-category', 'posted_date', '-posted_date', '-found_at']:
        found_items_list = found_items_list.order_by(sort_by)
    else:
        found_items_list = found_items_list.order_by('-found_at')

    # 🔥 ДЕБАГ ПОСЛЕ ВСЕХ ФИЛЬТРОВ - ДОБАВЛЕНО
    print(f"🔥 DEBUG: После всех фильтров: {found_items_list.count()} товаров")

    categories = FoundItem.objects.filter(
        search_query__user=request.user
    ).exclude(category__isnull=True).exclude(category='').values_list('category', flat=True).distinct()

    # 🔧 ИСПРАВЛЕНИЕ: Используем page_size из запроса вместо жесткого значения 20
    paginator = Paginator(found_items_list, page_size)
    page_number = request.GET.get('page')

    try:
        found_items = paginator.page(page_number)
    except PageNotAnInteger:
        found_items = paginator.page(1)
    except EmptyPage:
        found_items = paginator.page(paginator.num_pages)

    total_items = found_items_list.count()
    good_deals = found_items_list.filter(profit__gt=0).count()
    potential_profit = found_items_list.aggregate(total_profit=Sum('profit'))['total_profit'] or 0

    favorites_count = FoundItem.objects.filter(
        search_query__user=request.user,
        is_favorite=True
    ).count()

    # 🔥 ДЕБАГ ИНФОРМАЦИЯ В КОНТЕКСТЕ - ДОБАВЛЕНО
    print(f"🔥 DEBUG Контекст:")
    print(f"  - total_items: {total_items}")
    print(f"  - favorites_count: {favorites_count}")
    print(f"  - page_size: {page_size}")
    print(f"  - found_items paginator count: {found_items.paginator.count}")

    context = {
        'found_items': found_items,
        'categories': categories,
        'current_filters': {
            'category': category_filter,
            'price_min': price_min,
            'price_max': price_max,
            'seller_type': seller_type,
            'profitable_only': profitable_only,
            'sort_by': sort_by,
        },
        'stats': {
            'total_items': total_items,
            'good_deals': good_deals,
            'potential_profit': int(potential_profit)
        },
        'favorites_count': favorites_count,
        'is_favorites_view': is_favorites_view,
        'page_size': page_size,  # 🔧 ДОБАВЛЯЕМ page_size в контекст
    }
    return render(request, 'dashboard/found_items.html', context)


# ========== ИЗБРАННОЕ ==========

@require_POST
@csrf_exempt
@login_required
def toggle_favorite(request, item_id):
    """⭐ Переключает состояние избранного для товара с отправкой в Telegram

    ❤️ Добавляет/удаляет из избранного
    📱 Отправляет уведомление в Telegram при добавлении
    🔄 Обновляет счетчик избранных
    """
    try:
        # Получаем товар, проверяя что он принадлежит пользователю
        item = FoundItem.objects.get(id=item_id, search_query__user=request.user)

        # Парсим JSON данные из запроса
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        product_data = data.get('product_data', {})

        # Переключаем состояние избранного
        if item.is_favorite:
            item.is_favorite = False
            message = 'Товар удален из избранного'
            status = 'removed'
        else:
            item.is_favorite = True
            message = 'Товар добавлен в избранное'
            status = 'added'

            # Отправляем в Telegram в фоновом режиме
            if product_data:
                try:
                    import threading
                    thread = threading.Thread(
                        target=send_favorite_to_telegram,
                        args=(product_data, request.user)
                    )
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    logger.warning(f"Не удалось запустить поток для Telegram: {e}")

        item.save()

        # Получаем обновленное количество избранных
        favorites_count = FoundItem.objects.filter(
            search_query__user=request.user,
            is_favorite=True
        ).count()

        return JsonResponse({
            'status': status,
            'message': message,
            'favorites_count': favorites_count
        })

    except FoundItem.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Товар не найден или у вас нет доступа'
        }, status=404)

    except Exception as e:
        logger.error(f"❌ Ошибка переключения избранного: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)


@login_required
def favorites_list(request):
    """❤️ Страница с избранными товарами (только где is_favorite=True)

    📋 Отображает только избранные товары пользователя
    📊 Статистика по избранным товарам
    📈 Средняя прибыль, общая потенциальная прибыль
    """
    favorite_items = FoundItem.objects.filter(
        search_query__user=request.user,
        is_favorite=True
    ).order_by('-found_at')

    paginator = Paginator(favorite_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    stats = {
        'total_items': favorite_items.count(),
        'good_deals': favorite_items.filter(profit__gt=0).count(),
        'potential_profit': sum(item.profit for item in favorite_items if item.profit > 0),
        'avg_profit': favorite_items.filter(profit__gt=0).aggregate(Avg('profit'))['profit__avg'] or 0
    }

    context = {
        'found_items': page_obj,
        'stats': stats,
        'current_filters': {'active': False},
        'categories': FoundItem.objects.filter(
            search_query__user=request.user
        ).values_list('category', flat=True).distinct(),
        'is_favorites_page': True
    }

    return render(request, 'dashboard/favorites.html', context)


@login_required
def favorites_view(request):
    """❤️ Страница избранных товаров (альтернативная версия)

    🔍 Фильтрация через JavaScript на клиенте
    📋 Получает ID избранных товаров из localStorage
    """
    found_items = FoundItem.objects.filter(
        search_query__user=request.user,
        is_favorite=True
    ).order_by('-found_at')

    context = {
        'found_items': found_items,
    }
    return render(request, 'dashboard/favorites.html', context)


@login_required
def check_favorite(request, item_id):
    """🔍 Проверка, находится ли товар в избранном

    ✅ Возвращает boolean статус
    🔒 Проверяет права доступа к товару
    """
    try:
        item = FoundItem.objects.get(id=item_id, search_query__user=request.user)
        return JsonResponse({'is_favorite': item.is_favorite})
    except FoundItem.DoesNotExist:
        return JsonResponse({'is_favorite': False})


@login_required
def favorites_count(request):
    """📊 Получение количества избранных товаров

    🔢 Возвращает общее количество избранных
    👤 Только для текущего пользователя
    """
    count = FoundItem.objects.filter(search_query__user=request.user, is_favorite=True).count()
    return JsonResponse({'count': count})


# ========== ПОИСКОВЫЕ ЗАПРОСЫ ==========

@login_required
def search_queries_view(request):
    """🔍 Управление поисковых запросов

    ➕ Добавление новых поисковых запросов
    📋 Отображение всех запросов пользователя
    🎯 Настройка целевой цены, фильтров по цене
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        brand = request.POST.get('brand')
        min_price = request.POST.get('min_price', 0)
        max_price = request.POST.get('max_price', 1000000)
        target_price = request.POST.get('target_price')

        if name and target_price:
            search_query = SearchQuery(
                user=request.user,
                name=name,
                category=category if category else None,
                brand=brand if brand else None,
                min_price=min_price,
                max_price=max_price,
                target_price=target_price
            )
            search_query.save()
            messages.success(request, 'Поисковый запрос добавлен!')
            return redirect('search_queries')

    search_queries = SearchQuery.objects.filter(user=request.user)
    return render(request, 'dashboard/search_queries.html', {'search_queries': search_queries})


@login_required
def toggle_search_query(request, query_id):
    """🔘 Включение/выключение поискового запроса

    ⚡ Активация/деактивация мониторинга
    🔄 Изменение статуса is_active
    """
    search_query = get_object_or_404(SearchQuery, id=query_id, user=request.user)
    search_query.is_active = not search_query.is_active
    search_query.save()
    messages.success(request, f'Запрос {"активирован" if search_query.is_active else "деактивирован"}')
    return redirect('search_queries')


@login_required
def delete_search_query(request, query_id):
    """🗑️ Удаление поискового запроса

    ⚠️ Удаляет запрос и все связанные товары
    🔒 Проверяет права доступа
    """
    search_query = get_object_or_404(SearchQuery, id=query_id, user=request.user)
    search_query.delete()
    messages.success(request, 'Запрос удален')
    return redirect('search_queries')


# ========== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ TELEGRAM ==========

def send_favorite_to_telegram(product_data, user):
    """📨 Отправляет уведомление о добавлении в избранное в Telegram
        ❤️ Использует методы форматирования из notification_sender.py
        📸 Отправляет все фото через медиагруппу (как парсер)
        🔗 Ссылка внутри текста (без кнопок под текстом)
    """
    try:
        logger.info(f"🚀 Отправка избранного для {user.username}")

        # Добавляем недостающие поля для notification_sender
        if 'economy' not in product_data:
            economy = product_data.get('target_price', 0) - product_data.get('price', 0)
            product_data['economy'] = economy
            if product_data.get('target_price', 0) > 0:
                product_data['economy_percent'] = int((economy / product_data['target_price']) * 100)
            else:
                product_data['economy_percent'] = 0

        # Определяем source если нет
        if 'source' not in product_data:
            url = product_data.get('url', '').lower()
            if 'auto.ru' in url:
                product_data['source'] = 'auto.ru'
            else:
                product_data['source'] = 'avito'

        # Добавляем необходимые поля
        if 'avito_category' not in product_data and 'category' in product_data:
            product_data['avito_category'] = product_data['category']

        # Проверяем наличие rating полей
        if 'seller_rating' not in product_data:
            product_data['seller_rating'] = product_data.get('seller_rating', 5.0)

        if 'reviews_count' not in product_data:
            product_data['reviews_count'] = product_data.get('reviews_count', 0)

        # Проверяем seller_type
        if 'seller_type' not in product_data:
            seller_type = product_data.get('seller_type', '')
            if seller_type in ['Магазин', 'Компания', 'reseller']:
                product_data['seller_type'] = 'reseller'
            else:
                product_data['seller_type'] = 'private'

        # Используем notification_sender для форматирования
        try:
            from apps.parsing.utils.notification_sender import TelegramNotificationSender

            notification_sender = TelegramNotificationSender()

            # Определяем источник и форматируем сообщение
            source = product_data.get('source', '').lower()

            if 'auto.ru' in source:
                # Автомобиль с Auto.ru
                logger.info("🚗 Форматирование как Auto.ru")

                # Добавляем дополнительные поля для авто
                auto_fields = ['year', 'mileage', 'engine', 'transmission', 'drive',
                               'color', 'owners', 'pts', 'steering', 'body', 'package']
                for field in auto_fields:
                    if field not in product_data:
                        product_data[field] = ''

                message = notification_sender._format_auto_ru_message(product_data)
            else:
                # Товар с Авито
                logger.info("🏠 Форматирование как Авито")

                # Проверяем состояние товара
                if 'condition' not in product_data:
                    product_data['condition'] = 'Не указано'

                # Проверяем цвет
                if 'color' not in product_data:
                    product_data['color'] = 'Разноцветный'

                message = notification_sender._format_avito_message(product_data)

            # 1. ИЗМЕНЯЕМ ЗАГОЛОВОК на "ДОБАВЛЕНО В ИЗБРАННОЕ"
            lines = message.split('\n')
            for i, line in enumerate(lines):
                if 'ВЫГОДНАЯ СДЕЛКА' in line or 'ИНТЕРЕСНОЕ ПРЕДЛОЖЕНИЕ' in line or 'ИНТЕРЕСНЫЙ АВТОМОБИЛЬ' in line:
                    lines[i] = '❤️ <b>ДОБАВЛЕНО В ИЗБРАННОЕ</b>'
                    break

            # 2. ДОБАВЛЯЕМ ТЕГ #избранное
            for i, line in enumerate(lines):
                if line.startswith("#️⃣ <b>Теги:</b>"):
                    lines[i] = line + " #избранное"
                    break

            message = '\n'.join(lines)

            # Получаем токен и chat_id для отправки
            from shared.utils.config import get_bot_token, get_chat_id
            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                logger.error("❌ Токен или Chat ID не установлены")
                return False

            # 3. ПОЛУЧАЕМ ВСЕ ФОТО
            all_images = []

            # Сначала image_urls
            image_urls = product_data.get('image_urls', [])
            if image_urls:
                logger.info(f"📸 Найдено {len(image_urls)} изображений в image_urls")
                all_images = image_urls[:10]  # максимум 10 фото

            # Если нет image_urls, пробуем image_url
            if not all_images and product_data.get('image_url'):
                image_url = product_data['image_url']
                if image_url and isinstance(image_url, str) and image_url.strip():
                    logger.info(f"📸 Используем основное фото: {image_url}")
                    all_images = [image_url]

            logger.info(f"📸 Всего фото для отправки: {len(all_images)}")

            # Фильтруем валидные фото
            valid_image_urls = []
            for url in all_images:
                if url and isinstance(url, str) and url.strip():
                    # Пропускаем миниатюры
                    clean_url = url.split('?')[0]
                    if '128x96' not in clean_url and '64x48' not in clean_url and '32x24' not in clean_url:
                        valid_image_urls.append(url)

            logger.info(f"📸 Валидных фото после фильтрации: {len(valid_image_urls)}")

            from telegram import Bot, InputMediaPhoto
            import asyncio

            # Отправляем сообщение
            async def send_async():
                try:
                    bot = Bot(token=token)

                    # 4. ОТПРАВЛЯЕМ МЕДИАГРУППУ ЕСЛИ ЕСТЬ ФОТО
                    if valid_image_urls and len(valid_image_urls) > 0:
                        logger.info(f"📸 Отправляем медиа-группу из {len(valid_image_urls)} фото")

                        # Загружаем фото и создаем медиагруппу
                        media_group = []

                        for i, photo_url in enumerate(valid_image_urls[:10]):  # максимум 10
                            try:
                                if i == 0:
                                    # Первое фото с подписью (текстом сообщения)
                                    media = InputMediaPhoto(
                                        media=photo_url,
                                        caption=message,
                                        parse_mode='HTML'
                                    )
                                else:
                                    # Остальные фото без подписи
                                    media = InputMediaPhoto(
                                        media=photo_url
                                    )

                                media_group.append(media)
                                logger.info(f"✅ Добавлено фото {i + 1} в медиагруппу")

                            except Exception as e:
                                logger.warning(f"⚠️ Ошибка добавления фото {i + 1}: {e}")
                                continue

                        if media_group:
                            try:
                                await bot.send_media_group(
                                    chat_id=chat_id,
                                    media=media_group,
                                    read_timeout=60,
                                    write_timeout=60,
                                    connect_timeout=60
                                )
                                logger.info(f"✅ Медиагруппа из {len(media_group)} фото отправлена")
                                return True

                            except Exception as e:
                                logger.error(f"❌ Ошибка отправки медиагруппы: {e}")
                                # Fallback: отправляем только одно фото
                                logger.info("🔄 Fallback: отправляем одно фото")

                        # Fallback если медиагруппа не отправилась или пуста

                    # 5. ОТПРАВЛЯЕМ ОДНО ФОТО ИЛИ ТОЛЬКО ТЕКСТ
                    # 🔥 ВАЖНО: БЕЗ КНОПОК! Ссылка уже есть в тексте

                    image_url = product_data.get('image_url')
                    if image_url and isinstance(image_url, str) and image_url.strip() and not image_url.startswith(
                            'data:'):
                        try:
                            # Проверяем, что это не миниатюра
                            clean_url = image_url.split('?')[0]
                            if '128x96' not in clean_url and '64x48' not in clean_url:
                                await bot.send_photo(
                                    chat_id=chat_id,
                                    photo=image_url,
                                    caption=message,
                                    parse_mode='HTML'  # БЕЗ reply_markup!
                                )
                                logger.info(f"✅ Уведомление с одним фото отправлено")
                                return True
                        except Exception as photo_error:
                            logger.warning(f"⚠️ Не удалось отправить с фото: {photo_error}")

                    # Если не удалось отправить с фото - отправляем только текст
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='HTML',  # БЕЗ reply_markup!
                        disable_web_page_preview=True
                    )
                    logger.info(f"✅ Уведомление без фото отправлено")
                    return True

                except Exception as e:
                    logger.error(f"❌ Ошибка отправки уведомления: {e}")
                    import traceback
                    traceback.print_exc()
                    return False

            # Запускаем асинхронную отправку
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(send_async())
                return result
            finally:
                loop.close()

        except ImportError as e:
            logger.error(f"❌ Не удалось импортировать notification_sender: {e}")
            # Используем fallback метод
            return send_fallback_telegram_notification(product_data, user)

        except AttributeError as e:
            logger.error(f"❌ Методы форматирования не найдены в notification_sender: {e}")
            # Используем fallback метод
            return send_fallback_telegram_notification(product_data, user)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в send_favorite_to_telegram: {e}")
        import traceback
        traceback.print_exc()
        return False

@login_required
def profile_view(request):
    """👤 Настройки пользователя

    💰 Баланс и подписка
    📊 Статистика пользователя
    💳 История транзакций
    📱 Настройки Telegram
    """
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    try:
        user_subscription = UserSubscription.objects.filter(
            user=request.user,
            is_active=True,
            end_date__gte=timezone.now()
        ).select_related('plan').first()

        if user_subscription:
            days_remaining = (user_subscription.end_date - timezone.now()).days

            if user_subscription.plan.daily_price > 0:
                daily_price = user_subscription.plan.daily_price
            else:
                daily_price = user_subscription.plan.price / 30

            subscription_data = {
                'active': True,
                'plan': user_subscription.plan.plan_type,
                'plan_name': user_subscription.plan.name,
                'end_date': user_subscription.end_date,
                'days_remaining': days_remaining,
                'daily_price': daily_price
            }
        else:
            subscription_data = {
                'active': False,
                'plan': None,
                'plan_name': 'Не активна',
                'end_date': None,
                'days_remaining': 0,
                'daily_price': 0
            }
    except Exception as e:
        logger.error(f"Ошибка получения подписки: {e}")
        subscription_data = {
            'active': False,
            'plan': None,
            'plan_name': 'Ошибка загрузки',
            'end_date': None,
            'days_remaining': 0,
            'daily_price': 0
        }

    found_items_count = FoundItem.objects.filter(search_query__user=request.user).count()
    good_deals_count = FoundItem.objects.filter(search_query__user=request.user, profit__gt=0).count()
    active_searches_count = SearchQuery.objects.filter(user=request.user, is_active=True).count()
    today_items_count = FoundItem.objects.filter(
        search_query__user=request.user,
        found_at__date=timezone.now().date()
    ).count()

    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]

    context = {
        'user_profile': user_profile,
        'user_subscription': subscription_data,
        'transactions': transactions,
        'found_items_count': found_items_count,
        'good_deals_count': good_deals_count,
        'active_searches_count': active_searches_count,
        'today_items_count': today_items_count,
    }
    return render(request, 'dashboard/profile.html', context)

# ========== ПОДПИСКИ - ДИАГНОСТИКА ==========

@require_GET
@login_required
def debug_subscription_info(request):
    """💳 Диагностика информации о подписке

    📋 Проверка таблиц подписок в базе
    📊 Просмотр всех планов подписок
    👤 Проверка подписок текущего пользователя
    """
    from django.db import connection

    try:
        user = request.user

        with connection.cursor() as cursor:
            # 🔥 ИСПРАВЛЕНИЕ: PostgreSQL
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%%subscription%%'
            """)
            tables = cursor.fetchall()
            print("📋 Таблицы подписок:", tables)

            cursor.execute("SELECT * FROM website_subscriptionplan")
            plans = cursor.fetchall()
            print("📊 Планы подписок:", plans)

            cursor.execute("SELECT * FROM website_usersubscription WHERE user_id = %s", [user.id])
            user_subs = cursor.fetchall()
            print("👤 Подписки пользователя:", user_subs)

        from .models import SubscriptionPlan, UserSubscription

        all_plans = SubscriptionPlan.objects.all()
        print("🗂️ Все планы через ORM:")
        for plan in all_plans:
            add_to_console(f"   - {plan.name} ({plan.plan_type}): {plan.price} руб.")

        user_subscription = UserSubscription.objects.filter(
            user=user,
            is_active=True,
            end_date__gte=timezone.now()
        ).first()

        if user_subscription:
            add_to_console(f"✅ Активная подписка: {user_subscription.plan.name}")
        else:
            print("❌ Нет активной подписки")

        return JsonResponse({
            'status': 'success',
            'plans_count': all_plans.count(),
            'has_active_subscription': bool(user_subscription)
        })

    except Exception as e:
        add_to_console(f"❌ Ошибка диагностики: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def products_view(request):
    """🔄 Совместимость со старым кодом - перенаправляем на found_items

    🔄 Редирект для поддержки старых URL
    📦 Перенаправление на основную страницу товаров
    """
    return redirect('found_items')

@require_GET
@login_required
def debug_subscription_detailed(request):
    """📊 Детальная диагностика подписки

    🔍 Полная информация о активной подписке
    💰 Цена, тип, оставшееся время
    📅 Дата окончания подписки
    """
    try:
        user = request.user

        from django.utils import timezone
        from .models import UserSubscription

        user_subscription = UserSubscription.objects.filter(
            user=user,
            is_active=True,
            end_date__gte=timezone.now()
        ).select_related('plan').first()

        if user_subscription:
            subscription_info = {
                'plan_name': user_subscription.plan.name,
                'plan_type': user_subscription.plan.plan_type,
                'price': float(user_subscription.plan.price),
                'end_date': user_subscription.end_date.isoformat(),
                'days_left': (user_subscription.end_date - timezone.now()).days
            }

            print("📊 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ПОДПИСКЕ:")
            add_to_console(f"   - План: {subscription_info['plan_name']}")
            add_to_console(f"   - Тип: {subscription_info['plan_type']}")
            add_to_console(f"   - Цена: {subscription_info['price']} руб.")
            add_to_console(f"   - Дней осталось: {subscription_info['days_left']}")

            return JsonResponse({
                'status': 'success',
                'subscription': subscription_info
            })
        else:
            return JsonResponse({
                'status': 'success',
                'message': 'Активная подписка не найдена'
            })

    except Exception as e:
        add_to_console(f"❌ Ошибка детальной диагностики: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})


def test_subscription_notifications(request):
    """📢 Тестирование уведомлений о списаниях

    🔔 Отправка тестовых уведомлений всех типов
    🤖 Проверка привязки Telegram
    📊 Статистика успешных отправок
    """
    try:
        from django.contrib.auth.models import User
        from apps.website.utils.subscription_utils import send_test_subscription_notification
        import logging

        logger = logging.getLogger('subscriptions')

        if request.user.is_authenticated:
            user = request.user
        else:
            user = User.objects.filter(is_superuser=True).first()

        if not user:
            return JsonResponse({'status': 'error', 'message': 'Пользователь не найден'})

        from .models import UserProfile
        try:
            profile = UserProfile.objects.get(user=user)
            if not profile.telegram_user_id or not profile.telegram_verified:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Telegram не привязан. Привяжите Telegram в профиле.'
                })
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Профиль пользователя не найден'})

        notification_types = [
            'successful_charge',
            'low_balance_warning',
            'subscription_deactivated',
            'health_check'
        ]

        results = []

        for notification_type in notification_types:
            logger.info(f"🧪 Тестируем уведомление: {notification_type}")
            success = send_test_subscription_notification(user, notification_type)

            results.append({
                'type': notification_type,
                'success': success,
                'message': '✅ Отправлено' if success else '❌ Ошибка'
            })

        successful = sum(1 for r in results if r['success'])
        total = len(results)

        return JsonResponse({
            'status': 'success',
            'message': f'Тестирование завершено: {successful}/{total} уведомлений отправлено',
            'results': results,
            'user': user.username
        })

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования уведомлений: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ошибка: {str(e)}'})



# ========== ПОДПИСКИ И ПЛАТЕЖИ ==========

@require_POST
@csrf_exempt
@login_required
def activate_subscription(request):
    """💳 Активация подписки

    📋 Проверка баланса пользователя
    💰 Создание подписки на 30 дней
    📝 Запись транзакции в историю
    """
    try:
        data = json.loads(request.body)
        plan_type = data.get('plan_type')

        plan = SubscriptionPlan.objects.get(plan_type=plan_type, is_active=True)
        user_profile = UserProfile.objects.get(user=request.user)

        if user_profile.balance >= plan.price:
            end_date = timezone.now() + timedelta(days=30)
            subscription = UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                end_date=end_date,
                is_active=True
            )

            user_profile.balance -= plan.price
            user_profile.save()

            Transaction.objects.create(
                user=request.user,
                amount=-plan.price,
                transaction_type='subscription',
                status='completed',
                description=f'Активация подписки "{plan.name}"'
            )

            return JsonResponse({
                'status': 'success',
                'message': f'Подписка "{plan.name}" активирована'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Недостаточно средств на балансе'
            })

    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Тарифный план не найден'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
def create_subscription_payment(request):
    """💸 Создание транзакции для подписки с обновлением баланса

    🔒 Проверка достаточности средств
    📝 Создание транзакции списания
    💰 Автоматическое обновление баланса через save() модели
    """
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        plan_type = data.get('plan_type')

        if not amount or not plan_type:
            return JsonResponse({'status': 'error', 'message': 'Не указана сумма или тип плана'})

        user = request.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        if user_profile.balance < abs(float(amount)):
            return JsonResponse({
                'status': 'error',
                'message': f'Недостаточно средств. Текущий баланс: {user_profile.balance} ₽'
            })

        transaction = Transaction.objects.create(
            user=user,
            amount=-abs(float(amount)),
            transaction_type='subscription',
            status='completed',
            description=f'Оплата подписки {plan_type}'
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Подписка оплачена. Списано: {abs(float(amount))} ₽',
            'new_balance': float(user_profile.balance)
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_POST
@csrf_exempt
@login_required
def update_profile(request):
    """📝 Обновление профиля пользователя

    👤 Обновление имени, email
    📱 Обновление телефона, пола
    🖼️ Загрузка/удаление аватарки
    """
    try:
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        user_profile, created = UserProfile.objects.get_or_create(user=user)
        user_profile.phone = request.POST.get('phone', '')
        user_profile.gender = request.POST.get('gender', '')

        if 'avatar' in request.FILES:
            if user_profile.avatar:
                try:
                    if os.path.isfile(user_profile.avatar.path):
                        os.remove(user_profile.avatar.path)
                except (ValueError, OSError):
                    pass

            user_profile.avatar = request.FILES['avatar']

        if request.POST.get('clear_avatar') == 'true' and user_profile.avatar:
            try:
                if os.path.isfile(user_profile.avatar.path):
                    os.remove(user_profile.avatar.path)
            except (ValueError, OSError):
                pass
            user_profile.avatar = None

        user_profile.save()

        return JsonResponse({'status': 'success', 'message': 'Профиль успешно обновлен'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def send_fallback_telegram_notification(product_data, user):
    """📨 Fallback метод отправки в Telegram (упрощенная версия)"""
    try:
        from shared.utils.config import get_bot_token, get_chat_id
        from telegram import Bot, InputMediaPhoto
        import asyncio

        token = get_bot_token()
        chat_id = get_chat_id()

        if not token or not chat_id:
            logger.error("❌ Токен или Chat ID не установлены")
            return False

        # Рассчитываем экономию
        economy = product_data.get('target_price', 0) - product_data.get('price', 0)
        economy_percent = int((economy / product_data['target_price']) * 100) if product_data.get('target_price',
                                                                                                  0) > 0 else 0

        # Форматируем заголовок
        if economy > 0:
            header = "❤️ <b>ДОБАВЛЕНО В ИЗБРАННОЕ</b>"
            profit_text = f"💵 <b>Прибыль:</b> +{economy:,.0f} ₽ ({economy_percent}%)"
        else:
            header = "❤️ <b>ДОБАВЛЕНО В ИЗБРАННОЕ</b>"
            profit_text = f"⚖️ <b>Цена соответствует рынку</b>"

        # Форматируем продавца с рейтингом
        seller_name = product_data.get('seller_name', '')
        seller_rating = product_data.get('seller_rating', 0)
        reviews_count = product_data.get('reviews_count', 0)

        seller_text = seller_name
        if seller_rating > 0:
            stars = "★" * int(seller_rating) + "☆" * (5 - int(seller_rating))
            seller_text += f" ⭐ {stars} ({seller_rating}/5)"
            if reviews_count > 0:
                seller_text += f" ({reviews_count} отзывов)"

        # Собираем сообщение
        message_lines = []
        message_lines.append(header)
        message_lines.append("")
        message_lines.append(f"📦 <b>Товар:</b> {product_data.get('name', 'Неизвестный товар')}")
        message_lines.append(f"📍 <b>Город:</b> {product_data.get('city', 'Не указан')}")

        color = product_data.get('color', 'Разноцветный')
        if color:
            message_lines.append(f"🎨 <b>Цвет:</b> {color}")

        condition = product_data.get('condition', 'Не указано')
        if condition and condition != 'Не указано':
            message_lines.append(f"📦 <b>Состояние:</b> {condition}")

        message_lines.append(f"📂 <b>Категория:</b> {product_data.get('category', 'Не указана')}")
        message_lines.append("")
        message_lines.append(f"💎 <b>Цена продавца:</b> {product_data.get('price', 0):,.0f} ₽")
        message_lines.append(f"🎯 <b>Рыночная цена:</b> {product_data.get('target_price', 0):,.0f} ₽")
        message_lines.append(profit_text)
        message_lines.append("")
        message_lines.append(f"📅 <b>Размещено:</b> {product_data.get('posted_date', 'Дата не указана')}")

        views_count = product_data.get('views_count', 0)
        if views_count:
            message_lines.append(f"👁 <b>Просмотров:</b> {views_count}")

        message_lines.append(f"👤 <b>Продавец:</b> {seller_text}")

        # Описание
        description = product_data.get('description', '')
        if description and description not in ['Описание отсутствует', '']:
            clean_description = ' '.join(description.split())
            if len(clean_description) > 150:
                message_lines.append(f"\n📝 <b>Описание:</b> {clean_description[:150]}...")
            else:
                message_lines.append(f"\n📝 <b>Описание:</b> {clean_description}")

        # Генерируем хэштеги
        category = product_data.get('category', '').lower()
        name = product_data.get('name', '').lower()

        hashtags = []
        if 'мышь' in name or 'mouse' in name:
            hashtags.append('#мышь')
        if 'игров' in name or 'gaming' in name:
            hashtags.append('#игровая')
        if 'компьютер' in category or 'компьютер' in name:
            hashtags.append('#компьютер')
        if 'аксессуар' in category:
            hashtags.append('#аксессуары')

        hashtags.append('#избранное')
        hashtags.append('#автопоиск')

        if hashtags:
            message_lines.append(f"\n#️⃣ <b>Теги:</b> {' '.join(hashtags)}")

        message_lines.append("")
        message_lines.append(f"🔗 <a href='{product_data.get('url', '')}'>Просмотреть объявление на Авито</a>")

        message = "\n".join(message_lines)

        # Отправляем сообщение
        async def send_async():
            try:
                bot = Bot(token=token)

                # 1. Пробуем отправить медиагруппу со всеми фото
                image_urls = product_data.get('image_urls', [])
                if image_urls and len(image_urls) > 0:
                    media_group = []

                    for i, photo_url in enumerate(image_urls[:5]):  # максимум 5 фото
                        try:
                            if i == 0:
                                # Первое фото с подписью
                                media = InputMediaPhoto(
                                    media=photo_url,
                                    caption=message,
                                    parse_mode='HTML'
                                )
                            else:
                                media = InputMediaPhoto(
                                    media=photo_url
                                )

                            media_group.append(media)
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка добавления фото {i + 1}: {e}")
                            continue

                    if media_group:
                        try:
                            await bot.send_media_group(
                                chat_id=chat_id,
                                media=media_group,
                                read_timeout=60,
                                write_timeout=60,
                                connect_timeout=60
                            )
                            logger.info(f"✅ Fallback: медиагруппа из {len(media_group)} фото отправлена")
                            return True
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось отправить медиагруппу: {e}")

                # 2. Fallback: отправляем одно фото или только текст
                image_url = product_data.get('image_url')
                if image_url and not image_url.startswith('data:'):
                    try:
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=image_url,
                            caption=message,
                            parse_mode='HTML'  # БЕЗ КНОПОК!
                        )
                        logger.info(f"✅ Fallback уведомление с фото отправлено")
                        return True
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось отправить с фото: {e}")

                # 3. Отправляем только текст
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',  # БЕЗ КНОПОК!
                    disable_web_page_preview=True
                )
                logger.info(f"✅ Fallback уведомление без фото отправлено")
                return True

            except Exception as e:
                logger.error(f"❌ Ошибка fallback отправки: {e}")
                return False

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(send_async())
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Ошибка fallback метода: {e}")
        return False