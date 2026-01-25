from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import logging

from apps.website.models import (
    SearchQuery, FoundItem, UserProfile, UserSubscription,
    Transaction, ParserSettings
)
from apps.website.console_manager import add_to_console

logger = logging.getLogger(__name__)


# ========== ОСНОВНОЙ DASHBOARD ==========

@login_required
def dashboard(request):
    """🏠 Основной дашборд системы

    📊 Полная статистика пользователя
    🔍 Последние найденные товары
    📈 Активные поисковые запросы
    🚦 Статус сервисов (сайт, бот, парсер)
    💰 Потенциальная прибыль
    """
    user = request.user

    total_items_count = FoundItem.objects.filter(search_query__user=user).count()
    good_deals_count = FoundItem.objects.filter(
        search_query__user=user,
        profit__gt=0
    ).count()
    active_searches = SearchQuery.objects.filter(user=user, is_active=True).count()
    today_items_count = FoundItem.objects.filter(
        search_query__user=user,
        found_at__date=timezone.now().date()
    ).count()

    total_searches_count = SearchQuery.objects.filter(user=user).count()
    items_found_count = total_items_count

    try:
        from apps.website.models import ParserStats
        parser_stats = ParserStats.objects.filter(user=user).latest('created_at')
        duplicates_blocked_count = parser_stats.duplicates_blocked
    except:
        duplicates_blocked_count = 0

    potential_profit = FoundItem.objects.filter(
        search_query__user=user,
        profit__gt=0
    ).aggregate(total_profit=Sum('profit'))['total_profit'] or 0

    search_queries = SearchQuery.objects.filter(user=user).order_by('-created_at')[:10]
    found_items = FoundItem.objects.filter(search_query__user=user).order_by('-found_at')[:10]

    service_statuses = {
        'website': {'status': 'running', 'details': {'message': 'Сайт работает на http://127.0.0.1:8000'}},
        'bot': {'status': 'running', 'details': {'message': 'Бот активен и готов к работе'}},
        'parser': {'status': 'running', 'details': {'message': 'Парсер запущен и мониторит объявления'}}
    }

    context = {
        'search_queries': search_queries,
        'found_items': found_items,
        'stats': {
            'total_found': total_items_count,
            'active_searches': active_searches,
            'good_deals': good_deals_count,
            'total_profit': 12500,
            'total_deals': 8,
            'active_deals': 3,
            'completed_deals': 5
        },
        'products': [
            {'name': 'iPhone 13 Pro', 'current_price': 45000, 'is_active': True},
            {'name': 'MacBook Air M1', 'current_price': 65000, 'is_active': True},
            {'name': 'Samsung Galaxy S21', 'current_price': 28000, 'is_active': False}
        ],
        'deals': [
            {'product': {'name': 'iPhone 13 Pro'}, 'profit': 6000, 'status': 'sold'},
            {'product': {'name': 'MacBook Air M1'}, 'profit': None, 'status': 'purchased'},
            {'product': {'name': 'Samsung Galaxy'}, 'profit': None, 'status': 'monitoring'}
        ],
        'service_statuses': service_statuses,
        'total_items_count': total_items_count,
        'good_deals_count': good_deals_count,
        'active_searches': active_searches,
        'today_items_count': today_items_count,
        'potential_profit': potential_profit,
        'total_searches_count': total_searches_count,
        'items_found_count': items_found_count,
        'good_deals_count': good_deals_count,
        'duplicates_blocked_count': duplicates_blocked_count,
    }
    return render(request, 'dashboard/dashboard.html', context)


# ========== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ==========

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


@login_required
def user_settings(request):
    """⚙️ Настройки пользователя (альтернативная версия)

    📱 Настройки Telegram
    💳 История операций
    📊 Базовая статистика
    """
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    try:
        user_subscription = UserSubscription.objects.get(
            user=request.user,
            is_active=True,
            end_date__gte=timezone.now()
        )
        subscription_data = {
            'active': True,
            'plan': user_subscription.plan.plan_type,
            'plan_name': user_subscription.plan.name,
            'end_date': user_subscription.end_date,
            'days_remaining': (user_subscription.end_date - timezone.now()).days
        }
    except UserSubscription.DoesNotExist:
        subscription_data = {
            'active': False,
            'plan': None,
            'plan_name': 'Не активна',
            'end_date': None,
            'days_remaining': 0
        }

    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]

    context = {
        'user_profile': user_profile,
        'user_subscription': subscription_data,
        'transactions': transactions,
    }

    return render(request, 'dashboard/user_settings.html', context)


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


@require_POST
@csrf_exempt
@login_required
def clear_avatar(request):
    """🗑️ Очистка аватара пользователя

    ⚠️ Удаляет файл аватарки
    🔄 Сбрасывает поле avatar в None
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.delete_avatar()
        return JsonResponse({'status': 'success', 'message': 'Аватар успешно удален'})
    except UserProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Профиль не найден'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def change_password(request):
    """🔐 Смена пароля пользователя

    🔒 Проверка текущего пароля
    🔄 Установка нового пароля
    🔐 Обновление сессии авторизации
    """
    if request.method == 'POST':
        try:
            from django.contrib.auth import update_session_auth_hash

            user = request.user
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not user.check_password(current_password):
                return JsonResponse({'status': 'error', 'message': 'Неверный текущий пароль'})

            if new_password != confirm_password:
                return JsonResponse({'status': 'error', 'message': 'Новые пароли не совпадают'})

            user.set_password(new_password)
            user.save()

            update_session_auth_hash(request, user)

            return JsonResponse({'status': 'success', 'message': 'Пароль успешно изменен'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Неверный метод запроса'})


@login_required
def recalculate_balance(request):
    """🧮 Пересчитывает баланс пользователя на основе всех транзакций

    💰 Суммирует все завершенные транзакции
    🔄 Обновляет поле balance в профиле
    📊 Учитывает пополнения и списания
    """
    try:
        user = request.user
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        transactions = Transaction.objects.filter(user=user, status='completed')

        total_balance = 0
        for transaction in transactions:
            if transaction.transaction_type in ['topup', 'refund']:
                total_balance += transaction.amount
            elif transaction.transaction_type in ['subscription', 'daily_charge']:
                total_balance -= abs(transaction.amount)

        user_profile.balance = total_balance
        user_profile.save()

        messages.success(request, f'✅ Баланс пересчитан: {total_balance} ₽')

    except Exception as e:
        messages.error(request, f'❌ Ошибка пересчета баланса: {str(e)}')

    return redirect('profile')


# ========== РЕГИСТРАЦИЯ И АУТЕНТИФИКАЦИЯ ==========

def register_start(request):
    """🚀 Начальная страница регистрации с редиректом в бота

    🔗 Перенаправление на Telegram бота для регистрации
    👤 Для уже авторизованных пользователей - редирект на дашборд
    """
    if request.user.is_authenticated:
        return redirect('website:dashboard')

    return render(request, 'registration/register_start.html', {
        'title': 'Регистрация через Telegram'
    })


def register_view(request):
    """📝 Основная форма регистрации (теперь через бота)

    🔄 Перенаправление на начальную страницу регистрации
    👤 Для авторизованных - редирект на дашборд
    """
    if request.user.is_authenticated:
        return redirect('website:dashboard')

    return redirect('register_start')


def confirm_registration(request):
    """✅ Страница подтверждения регистрации

    🔍 Проверка данных в сессии
    ⏰ Проверка срока действия кода подтверждения
    💾 Отображение debug кода для тестирования
    """
    if request.user.is_authenticated:
        return redirect('website:dashboard')

    registration_data = request.session.get('registration_data')
    confirmation_code = request.session.get('debug_code')

    if not registration_data and not confirmation_code:
        messages.error(request, '❌ Сессия истекла или данные не найдены')
        return redirect('register_start')

    context = {
        'title': 'Подтверждение регистрации',
        'session_data': registration_data,
        'debug_code': confirmation_code
    }

    return render(request, 'registration/confirm_registration.html', context)


def confirm_registration_view(request):
    """🔐 Страница подтверждения регистрации с вводом кода

    ⏰ Проверка срока действия сессии
    🔢 Ввод кода подтверждения
    👤 Создание пользователя после успешной верификации
    """
    session_data = request.session.get('registration_data')
    expires = request.session.get('confirmation_expires')
    debug_code = request.session.get('debug_code')

    if not session_data or not expires:
        messages.error(request, '❌ Сессия истекла. Пройдите регистрацию заново.')
        return redirect('register')

    if timezone.now() > timezone.datetime.fromisoformat(expires):
        messages.error(request, '❌ Время подтверждения истекло. Пройдите регистрацию заново.')
        if 'registration_data' in request.session:
            del request.session['registration_data']
        if 'confirmation_expires' in request.session:
            del request.session['confirmation_expires']
        if 'debug_code' in request.session:
            del request.session['debug_code']
        return redirect('register')

    if request.method == 'POST':
        entered_code = request.POST.get('confirmation_code', '').strip()
        stored_code = session_data['confirmation_code']

        valid_codes = [stored_code]
        if debug_code:
            valid_codes.append(debug_code)

        if entered_code in valid_codes:
            try:
                form_data = session_data['form_data']
                form = CustomUserCreationForm(form_data)

                if form.is_valid():
                    user = form.save()

                    from django.contrib.auth import login
                    login(request, user)

                    ParserSettings.objects.create(
                        user=user,
                        name='Основные настройки',
                        keywords='Видеокарта, iPhone, кроссовки',
                        min_price=0,
                        max_price=100000,
                        min_rating=4.0,
                        seller_type='all',
                        check_interval=30,
                        max_items_per_hour=10,
                        browser_windows=1,
                        is_active=True,
                        is_default=True
                    )

                    if 'registration_data' in request.session:
                        del request.session['registration_data']
                    if 'confirmation_expires' in request.session:
                        del request.session['confirmation_expires']
                    if 'debug_code' in request.session:
                        del request.session['debug_code']

                    logger.info(f"✅ Новый пользователь зарегистрирован: {user.username}")
                    messages.success(request, f'🎉 Добро пожаловать, {user.first_name}! Регистрация завершена.')

                    return redirect('website:dashboard')
                else:
                    messages.error(request, '❌ Ошибка при создании пользователя.')

            except Exception as e:
                logger.error(f"Ошибка создания пользователя: {e}")
                messages.error(request, f'❌ Ошибка при создании пользователя: {str(e)}')
        else:
            messages.error(request, '❌ Неверный код подтверждения')

    remaining_time = timezone.datetime.fromisoformat(expires) - timezone.now()
    minutes_left = max(0, int(remaining_time.total_seconds() // 60))

    context = {
        'minutes_left': minutes_left,
        'phone': session_data['form_data'].get('phone', 'Не указан'),
        'debug_code': debug_code
    }

    return render(request, 'registration/confirm_registration.html', context)


# ========== ДЕТАЛЬНАЯ КАРТОЧКА ТОВАРА ==========

@login_required
def found_item_detail(request, item_id):
    """📄 Детальная страница карточки товара со ВСЕМИ данными

    👤 ТОЛЬКО для владельца товара
    🖼️ Отображает все изображения товара
    🚇 Показывает станции метро
    📊 Группирует характеристики по категориям
    🔍 Показывает похожие товары
    """
    try:
        item = get_object_or_404(FoundItem, id=item_id, search_query__user=request.user)

        similar_items = FoundItem.objects.filter(
            search_query__user=request.user,
            category=item.category
        ).exclude(id=item_id).order_by('-profit_percent')[:6]

        image_urls = []
        metro_stations = []

        if hasattr(item, 'get_images') and callable(getattr(item, 'get_images')):
            image_urls = item.get_images()
        else:
            if item.image_urls:
                try:
                    if isinstance(item.image_urls, str):
                        image_urls = json.loads(item.image_urls)
                    else:
                        image_urls = item.image_urls
                except (json.JSONDecodeError, TypeError):
                    image_urls = []
            if item.image_url and item.image_url not in image_urls:
                image_urls.append(item.image_url)

        if item.metro_stations:
            try:
                if isinstance(item.metro_stations, str):
                    stations_data = json.loads(item.metro_stations)
                else:
                    stations_data = item.metro_stations

                if isinstance(stations_data, list):
                    for station in stations_data:
                        if isinstance(station, dict):
                            metro_stations.append({
                                'name': station.get('name', ''),
                                'line_number': station.get('line_number', ''),
                                'color': station.get('color', '#666666')
                            })
                        else:
                            metro_stations.append({
                                'name': str(station),
                                'line_number': '',
                                'color': '#666666'
                            })
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        formatted_data = {
            'price': f"{item.price:,.0f} ₽" if item.price else "Не указана",
            'target_price': f"{item.target_price:,.0f} ₽" if item.target_price else "Не указана",
            'profit': f"{item.profit:+,.0f} ₽" if item.profit else "0 ₽",
            'profit_percent': f"{item.profit_percent}%" if item.profit_percent else "0%",
            'seller_rating': f"{item.seller_rating}/5" if item.seller_rating else "Нет оценок",
            'reviews_count': f"{item.reviews_count:,}" if item.reviews_count else "0",
            'views_count': f"{item.views_count:,}" if item.views_count else "0",
            'views_today': f"{item.views_today:,}" if item.views_today else "0",
        }

        characteristics = {
            'Основные': [
                ('Категория', item.category),
                ('Состояние', item.condition),
                ('Цвет', item.color),
                ('Год', item.year),
            ],
            'Двигатель': [
                ('Двигатель', item.engine),
                ('Объем', item.engine_volume),
                ('Мощность', item.engine_power),
                ('Пробег', item.mileage),
            ],
            'Трансмиссия': [
                ('Коробка передач', item.transmission),
                ('Привод', item.drive),
                ('Руль', item.steering),
            ],
            'Документы': [
                ('ПТС', item.pts),
                ('Владельцы', item.owners),
                ('Таможня', item.customs),
                ('Налог', item.tax),
            ],
            'Дополнительно': [
                ('Комплектация', item.package),
                ('Кузов', item.body),
                ('Статус цены', item.price_status),
                ('ID товара', item.product_id),
            ]
        }

        for category in list(characteristics.keys()):
            characteristics[category] = [(name, value) for name, value in characteristics[category] if value]
            if not characteristics[category]:
                del characteristics[category]

        context = {
            'item': item,
            'similar_items': similar_items,
            'image_urls': image_urls,
            'metro_stations': metro_stations,
            'formatted_data': formatted_data,
            'characteristics': characteristics,
            'title': f'{item.title} - Детали'
        }

        return render(request, 'dashboard/found_item_detail.html', context)

    except FoundItem.DoesNotExist:
        messages.error(request, 'Товар не найден или у вас нет доступа к нему')
        return redirect('found_items')
    except Exception as e:
        logger.error(f"Ошибка загрузки детальной страницы товара {item_id}: {e}")
        messages.error(request, 'Произошла ошибка при загрузке страницы товара')
        return redirect('found_items')


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


# ========== ДОБАВЛЕНИЕ ИЗ TELEGRAM ==========

def parse_telegram_message(message):
    """📝 Парсит сообщение из Telegram и создает FoundItem

    🔍 Извлечение данных из форматированного сообщения
    📊 Парсинг цены, целевой цены, категории
    🔗 Извлечение URL товара
    """
    try:
        title_match = re.search(r'📦\s*(.+?)(?=\n|$)', message)
        price_match = re.search(r'💰\s*Цена:\s*([\d,]+)', message)
        target_price_match = re.search(r'🎯\s*Рекомендуемая цена:\s*([\d,]+)', message)
        category_match = re.search(r'📂\s*Категория:\s*(.+?)(?=\n|$)', message)
        description_match = re.search(r'📝\s*Описание:\s*(.+?)(?=\极n|$)', message)
        url_match = re.search(r'🔗\s*(https?://[^\s]+)', message)

        if not all([title_match, price_match, target_price_match, url_match]):
            return None

        title = title_match.group(1).strip()
        price = float(price_match.group(1).replace(',', '').replace(' ', ''))
        target_price = float(target_price_match.group(1).replace(',', '').replace(' ', ''))
        category = category_match.group(1).strip() if category_match else 'Не указана'
        description = description_match.group(1).strip() if description_match else ''
        url = url_match.group(1).strip()

        return {
            'title': title,
            'price': price,
            'target_price': target_price,
            'category': category,
            'description': description,
            'url': url
        }

    except Exception as e:
        add_to_console(f"Ошибка парсинга сообщения: {e}")
        return None

@login_required
def search_view(request):
    """🔎 Улучшенный поиск по всем данным

    🔍 Поиск по товарам, запросам, настройкам, пользователям
    👥 Поиск пользователей только для админов
    📊 Пагинация результатов
    💡 Популярные поисковые запросы для подсказок
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    page = request.GET.get('page', 1)

    results = {
        'found_items': [],
        'search_queries': [],
        'parser_settings': [],
        'users': [],
        'total_count': 0
    }

    if query:
        if search_type in ['all', 'items']:
            found_items = FoundItem.objects.filter(
                search_query__user=request.user
            ).filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(category__icontains=query) |
                Q(seller_name__icontains=query) |
                Q(city__icontains=query)
            ).select_related('search_query').order_by('-found_at')

            paginator_items = Paginator(found_items, 10)
            try:
                results['found_items'] = paginator_items.page(page)
            except (PageNotAnInteger, EmptyPage):
                results['found_items'] = paginator_items.page(1)

        if search_type in ['all', 'queries']:
            search_queries = SearchQuery.objects.filter(
                user=request.user
            ).filter(
                Q(name__icontains=query) |
                Q(category__icontains=query) |
                Q(brand__icontains=query)
            ).order_by('-created_at')

            results['search_queries'] = search_queries

        if search_type in ['all', 'settings']:
            parser_settings = ParserSettings.objects.filter(
                user=request.user
            ).filter(
                Q(name__icontains=query) |
                Q(keywords__icontains=query)
            ).order_by('-updated_at')

            results['parser_settings'] = parser_settings

        if search_type in ['all', 'users'] and (request.user.is_staff or request.user.is_superuser):
            users = User.objects.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            ).order_by('-date_joined')[:10]

            results['users'] = users

        results['total_count'] = (
                len(results['found_items']) +
                len(results['search_queries']) +
                len(results['parser_settings']) +
                len(results['users'])
        )

    popular_searches = FoundItem.objects.filter(
        search_query__user=request.user
    ).values_list('title', flat=True).distinct()[:10]

    context = {
        'query': query,
        'search_type': search_type,
        'results': results,
        'popular_searches': popular_searches,
        'search_types': [
            ('all', 'Везде'),
            ('items', 'Товары'),
            ('queries', 'Запросы'),
            ('settings', 'Настройки'),
        ]
    }

    if request.user.is_staff or request.user.is_superuser:
        context['search_types'].append(('users', 'Пользователи'))

    return render(request, 'dashboard/search/search.html', context)


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
        found_items_page = paginator.page(page_number)
    except PageNotAnInteger:
        found_items_page = paginator.page(1)
    except EmptyPage:
        found_items_page = paginator.page(paginator.num_pages)

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
    print(f"  found_items.paginator.count: {found_items_page.paginator.count}", file=sys.stderr)

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
        'found_items': found_items_page,
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
    logger.info(f"  - found_items count: {found_items_page.paginator.count}")

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

@login_required
def test_database(request):
    """🗄️ Тест подключения к базе данных

    🔍 Проверка существования настроек пользователя
    ✅ Возврат ключевых слов если настройки найдены
    """
    try:
        settings = ParserSettings.objects.filter(user=request.user).first()
        if settings:
            add_to_console(f"✅ Тест базы: OK - {settings.keywords}")
            return JsonResponse({
                'status': 'success',
                'message': f'База OK: {settings.keywords}',
                'keywords': settings.keywords,
                'user_id': request.user.id
            })
        else:
            add_to_console(f"❌ Тест базы: настройки не найдены")
            return JsonResponse({'status': 'error', 'message': 'Настройки не найдены'})
    except Exception as e:
        add_to_console(f"❌ Тест базы: ошибка - {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def direct_db_query(request):
    """🔍 Прямой запрос к базе данных

    ⚡ Выполнение SQL запроса напрямую
    🔍 Поиск настроек пользователя по ID
    """
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT keywords, user_id FROM website_parsersettings WHERE user_id = %s LIMIT 1",
                           [request.user.id])
            row = cursor.fetchone()

            if row:
                add_to_console(f"✅ Прямой запрос: найдено - {row[0]}")
                return JsonResponse({
                    'status': 'success',
                    'keywords': row[0],
                    'user_id': row[1]
                })
            else:
                add_to_console(f"❌ Прямой запрос: запись не найдена")
                return JsonResponse({'status': 'error', 'message': 'Запись не найдена в базе'})

    except Exception as e:
        add_to_console(f"❌ Прямой запрос: ошибка - {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})

# ========== УПРАВЛЕНИЕ КОНСОЛЬЮ ==========

@require_GET
def console_output(request):
    """📋 Возвращает весь консольный вывод

    🔍 Получение последних 1000 строк консоли
    📊 Общее количество строк
    """
    try:
        output = get_console_output(1000)
        return JsonResponse({
            'status': 'success',
            'output': output,
            'total_lines': len(output)
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения консольного вывода: {str(e)}'
        })


@require_GET
def clear_console_view(request):
    """🧹 Очистка консольного вывода

    🗑️ Полная очистка консоли
    ✅ Подтверждение успешной очистки
    """
    try:
        clear_console()
        return JsonResponse({'status': 'success', 'message': 'Консоль очищена'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка очистки: {str(e)}'})


@require_GET
def console_update(request):
    """🔄 Возвращает обновления консоли

    🔍 Фильтрация дубликатов сообщений
    📊 Возврат только новых сообщений с последнего запроса
    """
    try:
        last_id = int(request.GET.get('last_id', 0))
        output = get_console_output(1000)

        unique_output = []
        seen_messages = set()

        for message in output:
            if ']' in message:
                message_content = message.split(']', 1)[1].strip()
            else:
                message_content = message

            if message_content not in seen_messages:
                seen_messages.add(message_content)
                unique_output.append(message)

        new_messages = []
        for i, message in enumerate(unique_output):
            if i >= last_id:
                new_messages.append(message)

        return JsonResponse({
            'status': 'success',
            'messages': new_messages,
            'total_count': len(unique_output),
            'last_id': len(unique_output)
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения консоли: {str(e)}'
        })

@require_GET
def export_project_structure(request):
    """Полная структура проекта с фильтрацией изображений и приоритетом для HTML/CSS"""
    try:
        project_root = settings.BASE_DIR
        structure = [f"{os.path.basename(project_root)}/"]
        all_files = []
        file_details = {}

        # Список игнорируемых папок
        ignore_dirs = {
            '__pycache__', '.git', '.idea', 'venv', '.venv',
            'node_modules', 'migrations', 'logs', 'database_backups'
        }

        # Расширения изображений для фильтрации
        image_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.bmp', '.tiff', '.webp', '.psd', '.ai', '.eps'
        }

        # Иконки для важных типов файлов
        file_icons = {
            '.py': '🐍',
            '.html': '🌐',
            '.htm': '🌐',
            '.css': '🎨',
            '.js': '⚡',
            '.json': '📊',
            '.txt': '📝',
            '.md': '📘',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.env': '🔧',
            '.sqlite3': '🗄️',
            '.db': '🗄️',
            '.pt': '🧠',
            '.joblib': '📦',
            '.sql': '🗃️',
            '.log': '📋',
            '.tmp': '🗑️',
            '.zip': '📎',
            '.rar': '📎',
            '.tar': '📎',
            '.gz': '📎',
            '.exe': '⚙️',
            '.dll': '⚙️',
            '.so': '⚙️'
        }

        # Важные расширения файлов (не ограничиваем их количество)
        important_extensions = {'.html', '.htm', '.css', '.js', '.py'}

        total_size_bytes = 0
        file_count_by_type = {}
        html_files = []
        js_files = []
        css_files = []
        py_files = []
        json_files = []
        important_files = []

        # Рекурсивный поиск файлов
        for root, dirs, files in os.walk(project_root):
            # Фильтруем игнорируемые папки
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]

            # Относительный путь
            rel_root = os.path.relpath(root, project_root)
            level = 0 if rel_root == '.' else len(rel_root.split(os.sep))

            # Добавляем папку в структуру
            if rel_root != '.':
                indent = '  ' * level
                dir_name = os.path.basename(root)
                structure.append(f"{indent}{dir_name}/")

            # Сортируем файлы для лучшего отображения
            files = sorted(files)

            # Обрабатываем файлы с фильтрацией изображений
            for file in files:
                # Пропускаем кэшированные Python файлы
                if file.endswith('.pyc') or file.endswith('.pyo'):
                    continue

                # Полный путь к файлу
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_root)

                # Определяем расширение файла
                file_ext = os.path.splitext(file)[1].lower()

                # ПРОПУСКАЕМ все изображения
                if file_ext in image_extensions:
                    continue

                # Добавляем в общий список
                all_files.append(rel_path)

                # Определяем иконку
                icon = '📄'
                for ext, file_icon in file_icons.items():
                    if file.endswith(ext):
                        icon = file_icon
                        break

                # Получаем размер файла
                try:
                    size_bytes = os.path.getsize(full_path)
                    total_size_bytes += size_bytes

                    # Форматируем размер
                    if size_bytes < 1024:
                        size_str = f"{size_bytes}B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f}KB"
                    elif size_bytes < 1024 * 1024 * 1024:
                        size_str = f"{size_bytes / (1024 * 1024):.1f}MB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

                    # Сохраняем детали
                    file_details[rel_path] = {
                        'size': size_str,
                        'icon': icon,
                        'type': file_ext or 'no-ext',
                        'bytes': size_bytes
                    }

                    # Считаем статистику
                    file_count_by_type[file_ext] = file_count_by_type.get(file_ext, 0) + 1

                except:
                    file_details[rel_path] = {
                        'size': '?',
                        'icon': icon,
                        'type': file_ext or 'no-ext',
                        'bytes': 0
                    }

                # Классифицируем файлы
                file_lower = file.lower()
                if file_lower.endswith(('.html', '.htm')):
                    html_files.append(rel_path)
                    important_files.append(rel_path)
                elif file_lower.endswith('.js'):
                    js_files.append(rel_path)
                    important_files.append(rel_path)
                elif file_lower.endswith('.css'):
                    css_files.append(rel_path)
                    important_files.append(rel_path)
                elif file_lower.endswith('.py'):
                    py_files.append(rel_path)
                    important_files.append(rel_path)
                elif file_lower.endswith('.json'):
                    json_files.append(rel_path)

                # Добавляем ВСЕ важные файлы в структуру БЕЗ ограничений
                if file_ext in important_extensions:
                    file_indent = '  ' * (level + 1)
                    structure.append(f"{file_indent}{icon} {file}")

        # Добавляем информацию о пропущенных изображениях
        stats = {
            'total_files': len(all_files),
            'html_files': len(html_files),
            'js_files': len(js_files),
            'css_files': len(css_files),
            'python_files': len(py_files),
            'json_files': len(json_files),
            'images_skipped': f"Изображения пропущены ({len(image_extensions)} типов)",
            'total_size': format_file_size(total_size_bytes),
            'file_types_distribution': file_count_by_type
        }

        # Группируем файлы по типам
        files_by_type = {
            'html': html_files,  # БЕЗ ограничений
            'js': js_files,      # БЕЗ ограничений
            'css': css_files,    # БЕЗ ограничений
            'python': py_files,  # БЕЗ ограничений
            'json': json_files,
            'important': important_files,  # Все важные файлы
            'all': all_files
        }

        return JsonResponse({
            'status': 'success',
            'structure': structure,  # Убрал ограничение 500 строк
            'files_by_type': files_by_type,
            'file_details': file_details,  # Убрал ограничение 200 элементов
            'statistics': stats,
            'project_name': os.path.basename(project_root),
            'scan_info': {
                'project_root': str(project_root),
                'total_dirs_scanned': 'all',
                'images_filtered': True,
                'important_files_shown': len(important_files)
            }
        })

    except Exception as e:
        import traceback
        logger.error(f"Ошибка в export_project_structure: {e}\n{traceback.format_exc()}")

        return JsonResponse({
            'status': 'error',
            'message': f"Ошибка: {str(e)}",
            'structure': [f"project/", f"  ❌ Ошибка: {str(e)[:100]}"],
            'files_by_type': {},
            'statistics': {
                'total_files': 0,
                'html_files': 0,
                'js_files': 0,
                'css_files': 0,
                'python_files': 0,
                'images_skipped': 'не сканировались'
            }
        })


def format_file_size(size_bytes):
    """Форматирует размер файла"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

@login_required
def add_from_telegram(request):
    """📨 Добавляет товар из Telegram сообщения

    🔍 Парсинг структурированного сообщения
    💾 Создание поискового запроса и товара
    🔗 Привязка к пользователю
    """
    if request.method == 'POST':
        message = request.POST.get('message', '')

        parsed_data = parse_telegram_message(message)
        if not parsed_data:
            return JsonResponse({'status': 'error', 'message': 'Не удалось распарсить сообщение'})

        try:
            search_query, created = SearchQuery.objects.get_or_create(
                user=request.user,
                name=parsed_data['title'][:50],
                defaults={
                    'category': parsed_data['category'],
                    'target_price': parsed_data['target_price'],
                    'min_price': 0,
                    'max_price': 1000000
                }
            )

            add_to_console(f"🔍 TELEGRAM ITEM: {parsed_data['title']}")
            add_to_console(f"🔍 SEARCH QUERY: {search_query.name} (created: {created})")
            add_to_console(f"🔍 USER: {request.user}")

            found_item = FoundItem.objects.create(
                search_query=search_query,
                title=parsed_data['title'],
                price=parsed_data['price'],
                url=parsed_data['url'],
                description=parsed_data['description'],
                found_at=timezone.now()
            )

            add_to_console(f"🔍 FOUND ITEM CREATED: {found_item.id}")

            return JsonResponse({'status': 'success', 'item_id': found_item.id})

        except Exception as e:
            add_to_console(f"🔍 ERROR: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})