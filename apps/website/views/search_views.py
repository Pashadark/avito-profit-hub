# website/views/search.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.db.models import Q, Avg, Max, Min, Sum
import json
from datetime import datetime, timedelta
from ..models import FoundItem, SearchQuery
import logging
import re

logger = logging.getLogger(__name__)


# ========== ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_item_icon(item):
    """Определяем иконку для товара"""
    icon_map = {
        'авто': 'ri-car-line',
        'недвижимость': 'ri-home-line',
        'техника': 'ri-smartphone-line',
        'одежда': 'ri-shopping-bag-3-line',
        'электроника': 'ri-computer-line',
        'мебель': 'ri-sofa-line',
        'спорт': 'ri-basketball-line',
        'детские': 'ri-child-line',
        'работа': 'ri-briefcase-line',
        'услуги': 'ri-service-line'
    }

    if item and item.category:
        category_lower = item.category.lower()
        for key, icon in icon_map.items():
            if key in category_lower:
                return icon

    return 'ri-search-line'


def format_price(price):
    """Форматируем цену"""
    if not price:
        return "Цена не указана"
    try:
        return f"{float(price):,.0f} ₽"
    except:
        return "Ошибка цены"


def format_profit(item):
    """Форматируем прибыль"""
    if item.profit and float(item.profit) > 0:
        return f"+{float(item.profit):,.0f} ₽"
    elif item.profit_percent and float(item.profit_percent) > 0:
        return f"+{item.profit_percent}%"
    return ""


def extract_car_brand(title):
    """Извлекаем марку автомобиля из названия"""
    if not title:
        return ""

    title_lower = title.lower()

    # Список марок автомобилей
    car_brands = [
        'toyota', 'kia', 'mazda', 'bmw', 'mercedes', 'audi', 'honda',
        'nissan', 'volkswagen', 'skoda', 'hyundai', 'renault', 'ford',
        'chevrolet', 'lexus', 'volvo', 'opel', 'peugeot', 'citroen',
        'mitsubishi', 'suzuki', 'subaru', 'jeep', 'land rover', 'porsche',
        'infiniti', 'acura', 'cadillac', 'chrysler', 'dodge', 'jaguar',
        'lada', 'moskvich', 'uaz', 'gaz', 'zaz', 'vaz'
    ]

    for brand in car_brands:
        if brand in title_lower:
            return brand.capitalize()

    return "Автомобиль"


# ========== БЫСТРЫЙ ПОИСК ДЛЯ ШАПКИ САЙТА (ИСПРАВЛЕННЫЙ) ==========

@require_GET
@login_required
def header_search_api(request):
    """🔍 УНИВЕРСАЛЬНЫЙ ПОИСК ПО ВСЕЙ БАЗЕ"""
    query = request.GET.get('q', '').strip().lower()

    print(f"\n🔍 УНИВЕРСАЛЬНЫЙ ПОИСК: '{query}'")

    if not query or len(query) < 2:
        return JsonResponse({
            'pages': [],
            'files': [],
            'members': [],
            'suggestions': []
        })

    try:
        # Берем ВСЕ товары из базы
        all_items = FoundItem.objects.all()
        print(f"📊 Всего товаров в базе: {all_items.count()}")

        # Ищем ВРУЧНУЮ по всем полям
        found_items = []

        for item in all_items:
            # Проверяем ВСЕ поля
            if (item.title and query in item.title.lower()) or \
                    (item.description and query in item.description.lower()) or \
                    (item.category and query in item.category.lower()) or \
                    (item.city and query in item.city.lower()) or \
                    (item.seller_name and query in item.seller_name.lower()) or \
                    (item.color and query in item.color.lower()) or \
                    (item.body and query in item.body.lower()) or \
                    (item.engine and query in item.engine.lower()) or \
                    (item.transmission and query in item.transmission.lower()) or \
                    (item.product_id and query in str(item.product_id).lower()) or \
                    (str(item.year) and query in str(item.year).lower()):

                found_items.append(item)
                if len(found_items) >= 10:  # максимум 10 результатов
                    break

        print(f"✅ Найдено товаров: {len(found_items)}")

        # Если ничего не нашли, пробуем найти ЛЮБОЕ совпадение
        if len(found_items) == 0:
            print("⚠️ Не найдено точных совпадений, ищем частичные...")

            for item in all_items:
                # Ищем в названии по словам
                if item.title:
                    words = item.title.lower().split()
                    for word in words:
                        if query in word or word in query:
                            if item not in found_items:
                                found_items.append(item)
                                break

                if len(found_items) >= 5:
                    break

        # Формируем ответ
        pages = []
        for item in found_items:
            # Определяем иконку
            icon = 'ri-car-line'
            if 'недвиж' in (item.category or '').lower():
                icon = 'ri-home-line'
            elif 'техник' in (item.category or '').lower():
                icon = 'ri-smartphone-line'
            elif 'электро' in (item.category or '').lower():
                icon = 'ri-computer-line'

            # Форматируем цену
            price_str = f"{float(item.price):,.0f} ₽" if item.price else "Цена не указана"

            # Прибыль
            profit_str = ""
            if item.profit and float(item.profit) > 0:
                profit_str = f"+{float(item.profit):,.0f} ₽"
            elif item.profit_percent and float(item.profit_percent) > 0:
                profit_str = f"+{item.profit_percent}%"

            pages.append({
                'id': item.id,
                'product_id': item.product_id or str(item.id),
                'name': item.title or 'Без названия',
                'description': (item.description or '')[:100],
                'category': item.category or 'Без категории',
                'location': item.city or '',
                'seller': item.seller_name or '',
                'price': price_str,
                'profit': profit_str,
                'icon': icon,
                'photo': item.image_url or '',
                'url': f'/found-items/{item.id}/',
                'year': str(item.year) if item.year else '',
                'color': item.color or '',
                'source': item.source or ''
            })

        # Подсказки
        suggestions = []
        if query and len(found_items) > 0:
            suggestions = [
                f"{query} в {found_items[0].city or 'Москве'}",
                f"{query} с фото",
                f"{query} новые"
            ]

        return JsonResponse({
            'pages': pages,
            'files': [],
            'members': [],
            'suggestions': suggestions,
            'query': query,
            'total_results': len(pages)
        })

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return JsonResponse({
            'pages': [],
            'files': [],
            'members': [],
            'suggestions': []
        })


# ========== ОСНОВНАЯ СТРАНИЦА ПОИСКА (С ОТЛАДКОЙ) ==========

@login_required
def search_view(request):
    """🔍 Основная страница поиска"""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')

    # ========== ОТЛАДКА ==========
    print("\n" + "=" * 80)
    print("📄 ВЫЗВАНА СТРАНИЦА ПОИСКА")
    print(f"📝 Запрос: '{query}'")
    print(f"👤 Пользователь: {request.user.username}")
    print(f"🔍 Тип поиска: {search_type}")
    print("=" * 80)
    # ========== КОНЕЦ ОТЛАДКИ ==========

    results = {
        'found_items': [],
        'search_queries': [],
        'total_count': 0
    }

    if query:
        # Поиск по товарам
        if search_type in ['all', 'items']:
            items = FoundItem.objects.filter(
                search_query__user=request.user
            ).filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(product_id__icontains=query) |
                Q(category__icontains=query) |
                Q(seller_name__icontains=query) |
                Q(city__icontains=query)
            ).select_related('search_query').order_by('-found_at')

            results['found_items'] = items[:50]
            print(f"📦 Найдено товаров: {len(results['found_items'])}")

        # Поиск по поисковым запросам
        if search_type in ['all', 'queries']:
            queries = SearchQuery.objects.filter(
                user=request.user,
                name__icontains=query
            ).order_by('-created_at')
            results['search_queries'] = queries
            print(f"📋 Найдено запросов: {len(results['search_queries'])}")

        results['total_count'] = len(results['found_items']) + len(results['search_queries'])
        print(f"🎯 Всего результатов: {results['total_count']}")

    context = {
        'query': query,
        'search_type': search_type,
        'results': results,
        'search_types': [
            ('all', 'Везде'),
            ('items', 'Товары'),
            ('queries', 'Запросы'),
        ]
    }

    print(f"📁 Используется шаблон: dashboard/search/search.html")
    print("=" * 80 + "\n")

    return render(request, 'dashboard/search/search.html', context)


# ========== РАСШИРЕННЫЙ ПОИСК ==========

@login_required
def advanced_search_view(request):
    """🎯 Расширенный поиск с фильтрами"""
    return render(request, 'dashboard/search/advanced_search.html')


# ========== УНИВЕРСАЛЬНЫЙ ПОИСК ПО БАЗЕ ОБЪЯВЛЕНИЙ ==========

@require_GET
@login_required
def universal_search_api(request):
    """🎯 Универсальный поиск по всем полям объявлений"""
    import traceback
    from django.db.models import Q
    from django.utils import timezone

    print(f"\n" + "=" * 80)
    print("🎯 УНИВЕРСАЛЬНЫЙ ПОИСК API")
    print(f"👤 Пользователь: {request.user.username}")
    print(f"🔍 Запрос: '{request.GET.get('q')}'")
    print("=" * 80)

    query = request.GET.get('q', '').strip().lower()
    per_page = int(request.GET.get('per_page', 50))

    try:
        # Если запрос пустой - возвращаем пустой результат
        if not query:
            print("⚠️ Пустой запрос")
            return JsonResponse({
                'status': 'success',
                'pages': [],
                'total': 0,
                'query': ''
            })

        # Ищем в реальной базе данных
        print(f"🔍 Ищем в реальной базе данных...")

        # Создаем Q-объект для поиска
        search_q = Q()

        # Основные поля для поиска
        search_q |= Q(title__icontains=query)
        search_q |= Q(description__icontains=query)
        search_q |= Q(product_id__icontains=query)
        search_q |= Q(category__icontains=query)
        search_q |= Q(seller_name__icontains=query)
        search_q |= Q(city__icontains=query)
        search_q |= Q(color__icontains=query)
        search_q |= Q(body__icontains=query)
        search_q |= Q(engine__icontains=query)
        search_q |= Q(transmission__icontains=query)

        # Поиск по году если это число
        if query.isdigit():
            try:
                year_query = int(query)
                if 1900 <= year_query <= 2100:
                    search_q |= Q(year=year_query)
            except:
                pass

        # Выполняем поиск (ТОЛЬКО РЕАЛЬНЫЕ ДАННЫЕ, БЕЗ ТЕСТОВЫХ)
        items = FoundItem.objects.filter(search_q)
        items_count = items.count()
        print(f"📊 Найдено товаров: {items_count}")

        # Сортируем по дате (новые сверху)
        items = items.order_by('-found_at')

        # Берем нужное количество
        items = items[:per_page]

        # Форматируем результаты
        results = []
        for item in items:
            try:
                # ФОТО
                photo_url = ''
                if hasattr(item, 'image_urls') and item.image_urls and len(item.image_urls) > 0:
                    photo_url = item.image_urls[0]
                elif hasattr(item, 'image_url') and item.image_url:
                    photo_url = item.image_url

                # ГОД
                year_str = ''
                if item.year:
                    try:
                        year_int = int(item.year)
                        if 1900 <= year_int <= 2100:
                            year_str = str(year_int)
                    except:
                        year_str = str(item.year)

                # ДАТА
                found_at_str = ''
                if item.found_at:
                    local_time = timezone.localtime(item.found_at)
                    found_at_str = local_time.strftime('%d.%m.%Y %H:%M')

                result_item = {
                    'id': item.id,
                    'title': item.title or 'Без названия',
                    'name': item.title or 'Без названия',
                    'description': (item.description or '')[:150] if item.description else '',
                    'category': item.category or 'Без категории',
                    'city': item.city or 'Не указан',
                    'seller_name': item.seller_name or '',
                    'seller_rating': float(item.seller_rating) if item.seller_rating else 0,
                    'price': float(item.price) if item.price else 0,
                    'profit': float(item.profit) if item.profit else 0,
                    'profit_percent': float(item.profit_percent) if item.profit_percent else 0,
                    'target_price': float(item.target_price) if item.target_price else 0,
                    'source': item.source or 'avito',
                    'year': year_str,
                    'mileage': item.mileage or '',
                    'color': item.color or '',
                    'photo': photo_url,
                    'image_url': photo_url,
                    'url': f'/found-items/{item.id}/',
                    'original_url': item.url or '',
                    'found_at': found_at_str,
                    'is_favorite': bool(item.is_favorite) if hasattr(item, 'is_favorite') else False,
                    'seller_avatar': item.seller_avatar or '',
                    'seller_profile_url': item.seller_profile_url or '',
                    'seller_type': item.seller_type or '',
                    'views_count': item.views_count or 0,
                    'reviews_count': item.reviews_count or 0,
                    'engine': item.engine or '',
                    'transmission': item.transmission or '',
                    'drive': item.drive or '',
                    'body': item.body or '',
                    'steering': item.steering or '',
                    'owners': item.owners or '',
                    'pts': item.pts or '',
                    'package': item.package or '',
                    'condition': item.condition or '',
                    'product_id': item.product_id or ''
                }
                results.append(result_item)
            except Exception as e:
                print(f"⚠️ Ошибка форматирования товара {item.id}: {e}")
                continue

        print(f"📤 Отправляем {len(results)} РЕАЛЬНЫХ результатов")
        print("=" * 80)

        return JsonResponse({
            'status': 'success',
            'pages': results,
            'total': len(results),
            'query': query
        })

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(traceback.format_exc())
        print("=" * 80)

        return JsonResponse({
            'status': 'error',
            'pages': [],
            'total': 0,
            'error': str(e)
        }, status=500)

def calculate_search_score(item, query):
    """Вычисляем релевантность поиска"""
    score = 0
    query_lower = query.lower()

    # Высокий приоритет: ID и название
    if item.product_id and query_lower in str(item.product_id).lower():
        score += 100
    if item.title and query_lower in item.title.lower():
        score += 50

    # Средний приоритет: категория, продавец, город
    if item.category and query_lower in item.category.lower():
        score += 30
    if item.seller_name and query_lower in item.seller_name.lower():
        score += 20
    if item.city and query_lower in item.city.lower():
        score += 20

    # Низкий приоритет: остальные поля
    fields = ['description', 'color', 'year', 'mileage', 'engine',
              'transmission', 'body', 'steering', 'condition']

    for field in fields:
        value = getattr(item, field, '')
        if value and query_lower in str(value).lower():
            score += 10

    return score


# ========== ДРУГИЕ ФУНКЦИИ (без изменений) ==========

@require_GET
@login_required
def table_search_api(request):
    """📊 Поиск для таблицы с фильтрами и сортировкой"""
    try:
        # Получаем фильтры из GET параметров
        filters = {}

        # Текстовые фильтры
        text_fields = ['title', 'category', 'city', 'color', 'seller_name',
                       'seller_type', 'condition', 'source']

        for field in text_fields:
            value = request.GET.get(field)
            if value and value != 'all':
                filters[f'{field}__icontains'] = value

        # Числовые фильтры
        numeric_fields = ['price', 'profit', 'year', 'views_count', 'seller_rating']
        for field in numeric_fields:
            min_val = request.GET.get(f'{field}_min')
            max_val = request.GET.get(f'{field}_max')

            if min_val:
                filters[f'{field}__gte'] = float(min_val)
            if max_val:
                filters[f'{field}__lte'] = float(max_val)

        # Специальные фильтры
        if request.GET.get('profitable_only') == 'true':
            filters['profit__gt'] = 0

        if request.GET.get('favorites_only') == 'true':
            filters['is_favorite'] = True

        # Базовый QuerySet
        items = FoundItem.objects.filter(
            search_query__user=request.user,
            **filters
        ).select_related('search_query')

        # Сортировка
        sort_by = request.GET.get('sort', '-found_at')
        sort_field = sort_by.lstrip('-')

        if sort_field in ['price', 'profit', 'profit_percent', 'seller_rating',
                          'views_count', 'year', 'found_at', 'posted_date']:
            items = items.order_by(sort_by)

        # Пагинация
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        start = (page - 1) * per_page
        end = start + per_page

        total_count = items.count()
        items_page = items[start:end]

        # Форматируем данные для таблицы
        data = []
        for item in items_page:
            data.append({
                'id': item.id,
                'product_id': item.product_id or item.id,
                'title': item.title or 'Без названия',
                'source': item.source or 'avito',
                'image_url': item.image_url or item.photo or '',
                'seller_rating': float(item.seller_rating) if item.seller_rating else 0,
                'reviews_count': item.reviews_count or 0,
                'posted_date': item.posted_date.strftime('%d.%m.%Y') if item.posted_date else '-',
                'views_count': item.views_count or 0,
                'views_today': item.views_today or 0,
                'condition': item.condition or '-',
                'category': item.category or '-',
                'city': item.city or '-',
                'mileage': item.mileage or '-',
                'year': item.year or '-',
                'color': item.color or '-',
                'price': int(item.price) if item.price else 0,
                'profit': int(item.profit) if item.profit else 0,
                'profit_percent': float(item.profit_percent) if item.profit_percent else 0,
                'price_status': item.price_status or '-',
                'created_at': item.found_at.strftime('%d.%m.%Y %H:%M'),
                'is_favorite': bool(item.is_favorite),
                'target_price': int(item.target_price) if item.target_price else 0,
                'url': item.url or '',
                'description': item.description or '',
                'seller_name': item.seller_name or '',
                'seller_type': item.seller_type or 'Не указано',
                'address': item.address or '',
                'metro_stations': item.metro_stations or [],
                'steering': item.steering or '-',
                'transmission': item.transmission or '-',
                'drive': item.drive or '-',
                'engine': item.engine or '-',
                'owners': item.owners or '-',
                'pts': item.pts or '-',
                'tax': item.tax or '-',
                'customs': item.customs or '-',
                'body': item.body or '-',
                'package': item.package or '-',
                'discount_price': int(item.discount_price) if item.discount_price else 0
            })

        # Статистика
        stats = {
            'total': total_count,
            'profitable': items.filter(profit__gt=0).count(),
            'avg_price': items.aggregate(avg_price=Avg('price'))['avg_price'] or 0,
            'avg_profit': items.aggregate(avg_profit=Avg('profit'))['avg_profit'] or 0,
            'total_profit': items.aggregate(total_profit=Sum('profit'))['total_profit'] or 0
        }

        return JsonResponse({
            'status': 'success',
            'items': data,
            'stats': stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Ошибка поиска для таблицы: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_GET
@login_required
def autocomplete_api(request):
    """✨ API для автодополнения полей"""
    field = request.GET.get('field', '')
    query = request.GET.get('q', '').strip()

    if not field or not query or len(query) < 2:
        return JsonResponse({'results': []})

    try:
        results = []

        if field == 'category':
            categories = FoundItem.objects.filter(
                search_query__user=request.user,
                category__icontains=query
            ).exclude(category__isnull=True).exclude(category='').values_list(
                'category', flat=True
            ).distinct().order_by('category')[:10]

            results = [{'id': cat, 'text': cat} for cat in categories]

        elif field == 'city':
            cities = FoundItem.objects.filter(
                search_query__user=request.user,
                city__icontains=query
            ).exclude(city__isnull=True).exclude(city='').values_list(
                'city', flat=True
            ).distinct().order_by('city')[:10]

            results = [{'id': city, 'text': city} for city in cities]

        elif field == 'seller':
            sellers = FoundItem.objects.filter(
                search_query__user=request.user,
                seller_name__icontains=query
            ).exclude(seller_name__isnull=True).exclude(seller_name='').values_list(
                'seller_name', flat=True
            ).distinct().order_by('seller_name')[:10]

            results = [{'id': seller, 'text': seller} for seller in sellers]

        elif field == 'color':
            colors = FoundItem.objects.filter(
                search_query__user=request.user,
                color__icontains=query
            ).exclude(color__isnull=True).exclude(color='').values_list(
                'color', flat=True
            ).distinct().order_by('color')[:10]

            results = [{'id': color, 'text': color} for color in colors]

        return JsonResponse({'results': results})

    except Exception as e:
        logger.error(f"Ошибка автодополнения: {e}")
        return JsonResponse({'results': []})


@require_GET
@login_required
def search_filters_api(request):
    """🎛️ Получение доступных фильтров для поиска"""
    try:
        # Уникальные категории
        categories = FoundItem.objects.filter(
            search_query__user=request.user
        ).exclude(category__isnull=True).exclude(category='').values_list(
            'category', flat=True
        ).distinct().order_by('category')

        # Уникальные города
        cities = FoundItem.objects.filter(
            search_query__user=request.user
        ).exclude(city__isnull=True).exclude(city='').values_list(
            'city', flat=True
        ).distinct().order_by('city')

        # Уникальные источники
        sources = FoundItem.objects.filter(
            search_query__user=request.user
        ).exclude(source__isnull=True).exclude(source='').values_list(
            'source', flat=True
        ).distinct().order_by('source')

        # Уникальные типы продавцов
        seller_types = FoundItem.objects.filter(
            search_query__user=request.user
        ).exclude(seller_type__isnull=True).exclude(seller_type='').values_list(
            'seller_type', flat=True
        ).distinct().order_by('seller_type')

        # Уникальные цвета
        colors = FoundItem.objects.filter(
            search_query__user=request.user
        ).exclude(color__isnull=True).exclude(color='').values_list(
            'color', flat=True
        ).distinct().order_by('color')

        # Минимальные и максимальные значения
        price_stats = FoundItem.objects.filter(
            search_query__user=request.user
        ).aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price')
        )

        year_stats = FoundItem.objects.filter(
            search_query__user=request.user
        ).exclude(year__isnull=True).aggregate(
            min_year=Min('year'),
            max_year=Max('year')
        )

        return JsonResponse({
            'categories': list(categories),
            'cities': list(cities),
            'sources': list(sources),
            'seller_types': list(seller_types),
            'colors': list(colors),
            'price_range': {
                'min': price_stats['min_price'] or 0,
                'max': price_stats['max_price'] or 1000000,
                'avg': price_stats['avg_price'] or 0
            },
            'year_range': {
                'min': year_stats['min_year'] or 2000,
                'max': year_stats['max_year'] or datetime.now().year
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения фильтров: {e}")
        return JsonResponse({
            'categories': [],
            'cities': [],
            'sources': [],
            'seller_types': [],
            'colors': [],
            'price_range': {'min': 0, 'max': 1000000, 'avg': 0},
            'year_range': {'min': 2000, 'max': datetime.now().year}
        })


# ========== УПРАВЛЕНИЕ ПОИСКОВЫМИ ЗАПРОСАМИ ==========

@login_required
def search_queries_view(request):
    """📋 Управление поисковыми запросами"""
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
                target_price=target_price,
                is_active=True
            )
            search_query.save()
            from django.contrib import messages
            messages.success(request, 'Поисковый запрос добавлен!')
            from django.shortcuts import redirect
            return redirect('search_queries')

    search_queries = SearchQuery.objects.filter(user=request.user)
    return render(request, 'dashboard/search_queries.html', {'search_queries': search_queries})


@login_required
def toggle_search_query(request, query_id):
    """🔘 Включение/выключение поискового запроса"""
    search_query = SearchQuery.objects.get(id=query_id, user=request.user)
    search_query.is_active = not search_query.is_active
    search_query.save()
    from django.contrib import messages
    messages.success(request, f'Запрос {"активирован" if search_query.is_active else "деактивирован"}')
    from django.shortcuts import redirect
    return redirect('search_queries')


@login_required
def delete_search_query(request, query_id):
    """🗑️ Удаление поискового запроса"""
    search_query = SearchQuery.objects.get(id=query_id, user=request.user)
    search_query.delete()
    from django.contrib import messages
    messages.success(request, 'Запрос удален')
    from django.shortcuts import redirect
    return redirect('search_queries')


# ========== ЭКСПОРТ РЕЗУЛЬТАТОВ ПОИСКА ==========

@require_GET
@login_required
def export_search_results(request):
    """📥 Экспорт результатов поиска"""
    import csv
    from django.http import HttpResponse
    from io import StringIO

    query = request.GET.get('q', '')
    filters = json.loads(request.GET.get('filters', '{}'))

    try:
        # Применяем те же фильтры что и в поиске
        items = FoundItem.objects.filter(search_query__user=request.user)

        if query:
            items = items.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(product_id__icontains=query) |
                Q(category__icontains=query) |
                Q(seller_name__icontains=query) |
                Q(city__icontains=query)
            )

        # Применяем фильтры
        if filters.get('category'):
            items = items.filter(category__icontains=filters['category'])
        if filters.get('city'):
            items = items.filter(city__icontains=filters['city'])
        if filters.get('min_price'):
            items = items.filter(price__gte=float(filters['min_price']))
        if filters.get('max_price'):
            items = items.filter(price__lte=float(filters['max_price']))
        if filters.get('profitable_only'):
            items = items.filter(profit__gt=0)

        items = items.order_by('-found_at')

        output = StringIO()
        writer = csv.writer(output)

        # Заголовки
        headers = [
            'ID', 'Product ID', 'Название', 'Категория', 'Цена',
            'Целевая цена', 'Прибыль', 'Прибыль %', 'Город', 'Продавец',
            'Тип продавца', 'Рейтинг', 'Отзывы', 'Просмотры',
            'Год', 'Цвет', 'Пробег', 'Двигатель', 'КПП', 'Привод',
            'Кузов', 'Руль', 'Владельцы', 'ПТС', 'Налог', 'Растаможка',
            'Комплектация', 'Состояние', 'Источник', 'Дата публикации',
            'Дата находки', 'Ссылка', 'Описание'
        ]

        writer.writerow(headers)

        # Данные
        for item in items:
            writer.writerow([
                item.id,
                item.product_id or '',
                item.title or '',
                item.category or '',
                item.price or 0,
                item.target_price or 0,
                item.profit or 0,
                item.profit_percent or 0,
                item.city or '',
                item.seller_name or '',
                item.seller_type or '',
                item.seller_rating or 0,
                item.reviews_count or 0,
                item.views_count or 0,
                item.year or '',
                item.color or '',
                item.mileage or '',
                item.engine or '',
                item.transmission or '',
                item.drive or '',
                item.body or '',
                item.steering or '',
                item.owners or '',
                item.pts or '',
                item.tax or '',
                item.customs or '',
                item.package or '',
                item.condition or '',
                item.source or '',
                item.posted_date.strftime('%d.%m.%Y %H:%M') if item.posted_date else '',
                item.found_at.strftime('%d.%m.%Y %H:%M'),
                item.url or '',
                (item.description or '')[:500]
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response[
            'Content-Disposition'] = f'attachment; filename="search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        return response

    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ========== ПОИСК С ДИНАМИЧЕСКИМИ ПОДСКАЗКАМИ ==========

@require_GET
@login_required
def dynamic_search_api(request):
    """⚡ Ультрабыстрый поиск с подсказками для UI"""
    query = request.GET.get('q', '').strip().lower()

    if not query or len(query) < 2:
        return JsonResponse({'items': [], 'suggestions': []})

    try:
        # Ищем по всем полям
        items = FoundItem.objects.filter(
            search_query__user=request.user
        ).filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query) |
            Q(city__icontains=query) |
            Q(seller_name__icontains=query) |
            Q(product_id__icontains=query) |
            Q(color__icontains=query) |
            Q(year__icontains=query)
        ).order_by('-found_at')[:10]

        results = []
        for item in items:
            results.append({
                'id': item.id,
                'name': item.title or 'Без названия',
                'description': (item.description or '')[:100],
                'category': item.category or 'Без категории',
                'location': item.city or '',
                'seller': item.seller_name or '',
                'price': f"{item.price:,.0f} ₽" if item.price else "Цена не указана",
                'profit': f"+{item.profit:,.0f} ₽" if item.profit and item.profit > 0 else '',
                'icon': get_item_icon(item),
                'photo': item.image_url or item.photo or '',
                'url': f'/found-items/{item.id}/',
                'source': item.source or '',
                'year': str(item.year) if item.year else '',
                'color': item.color or '',
                'is_favorite': bool(item.is_favorite)
            })

        # Формируем подсказки
        suggestions = []
        if query:
            # Популярные категории
            categories = FoundItem.objects.filter(
                search_query__user=request.user,
                category__icontains=query
            ).values_list('category', flat=True).distinct()[:3]

            # Популярные города
            cities = FoundItem.objects.filter(
                search_query__user=request.user,
                city__icontains=query
            ).values_list('city', flat=True).distinct()[:3]

            # Марки автомобилей
            car_brands = ['Toyota', 'Mazda', 'Kia', 'BMW', 'Mercedes', 'Audi', 'Honda']
            brands = [brand for brand in car_brands if query.lower() in brand.lower()][:3]

            suggestions = list(categories) + list(cities) + brands

        return JsonResponse({
            'items': results,
            'suggestions': suggestions[:5],
            'total': len(results)
        })

    except Exception as e:
        logger.error(f"Ошибка динамического поиска: {e}")
        return JsonResponse({'items': [], 'suggestions': [], 'error': str(e)})


# ========== ПОИСК ПО САЙТУ ==========

@require_GET
@login_required
def site_search_api(request):
    """🌐 Поиск с указанием сайта (avito/auto.ru)"""
    query = request.GET.get('q', '').strip()
    site = request.GET.get('site', 'all')

    if not query:
        return JsonResponse({'items': [], 'total': 0})

    try:
        items = FoundItem.objects.filter(
            search_query__user=request.user
        )

        if site != 'all':
            items = items.filter(source=site)

        # Расширенный поиск
        items = items.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query) |
            Q(seller_name__icontains=query) |
            Q(city__icontains=query) |
            Q(product_id__icontains=query) |
            Q(year__icontains=query) |
            Q(color__icontains=query) |
            Q(body__icontains=query) |
            Q(engine__icontains=query) |
            Q(transmission__icontains=query) |
            Q(mileage__icontains=query)
        ).order_by('-found_at')

        # Статистика
        stats = {
            'total': items.count(),
            'avito': items.filter(source='avito').count(),
            'auto_ru': items.filter(source='auto_ru').count(),
            'profitable': items.filter(profit__gt=0).count(),
            'avg_price': items.aggregate(avg=Avg('price'))['avg'] or 0,
            'total_profit': items.aggregate(sum=Sum('profit'))['sum'] or 0
        }

        # Пагинация
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        start = (page - 1) * per_page
        end = start + per_page

        items_page = items[start:end]

        results = []
        for item in items_page:
            results.append({
                'id': item.id,
                'title': item.title or 'Без названия',
                'price': item.price or 0,
                'target_price': item.target_price or 0,
                'profit': item.profit or 0,
                'profit_percent': item.profit_percent or 0,
                'category': item.category or '',
                'city': item.city or '',
                'seller_name': item.seller_name or '',
                'seller_rating': item.seller_rating or 0,
                'year': item.year,
                'mileage': item.mileage or '',
                'color': item.color or '',
                'source': item.source or '',
                'image_url': item.image_url or item.photo or '',
                'url': f'/found-items/{item.id}/',
                'original_url': item.url or '',
                'found_at': item.found_at.strftime('%d.%m.%Y %H:%M'),
                'is_favorite': bool(item.is_favorite)
            })

        return JsonResponse({
            'items': results,
            'stats': stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': stats['total'],
                'pages': (stats['total'] + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Ошибка поиска по сайту: {e}")
        return JsonResponse({'items': [], 'stats': {}, 'error': str(e)})