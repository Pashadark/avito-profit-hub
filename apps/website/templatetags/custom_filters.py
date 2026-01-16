from django import template
from datetime import datetime, timedelta
import re
from django.utils import timezone
import calendar
from urllib.parse import urlencode
from django.http import QueryDict

register = template.Library()

# Словарь для преобразования русских названий месяцев
RUSSIAN_MONTHS = {
    'Января': 1, 'Февраля': 2, 'Марта': 3, 'Апреля': 4,
    'Мая': 5, 'Июня': 6, 'Июля': 7, 'Августа': 8,
    'Сентября': 9, 'Октября': 10, 'Ноября': 11, 'Декабря': 12
}


@register.filter
def subtract(value, arg):
    """Вычитает arg из value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def parse_avito_date(posted_date_str, found_at):
    """Парсит строку даты из Avito в datetime объект"""
    if not posted_date_str:
        return None

    try:
        posted_date_str = posted_date_str.lower().strip()

        # Формат "сегодня в HH:MM"
        if "Сегодня" in posted_date_str:
            time_str = re.search(r'в (\d{1,2}:\d{2})', posted_date_str)
            if time_str:
                time_part = time_str.group(1)
                today = found_at.date()
                posted_time = datetime.strptime(time_part, "%H:%M").time()
                posted_datetime = datetime.combine(today, posted_time)
                return timezone.make_aware(posted_datetime)

        # Формат "вчера в HH:MM"
        elif "Вчера" in posted_date_str:
            time_str = re.search(r'в (\d{1,2}:\d{2})', posted_date_str)
            if time_str:
                time_part = time_str.group(1)
                yesterday = found_at.date() - timedelta(days=1)
                posted_time = datetime.strptime(time_part, "%H:%M").time()
                posted_datetime = datetime.combine(yesterday, posted_time)
                return timezone.make_aware(posted_datetime)

        # Формат "1 сентября в HH:MM"
        elif any(month in posted_date_str for month in RUSSIAN_MONTHS.keys()):
            match = re.search(r'(\d{1,2})\s+([а-я]+)\s+в\s+(\d{1,2}:\d{2})', posted_date_str)
            if match:
                day = int(match.group(1))
                month_name = match.group(2)
                time_str = match.group(3)

                month = RUSSIAN_MONTHS.get(month_name)
                if month:
                    current_year = found_at.year
                    # Проверяем, не в будущем ли месяце (например, декабрь в январе)
                    if month > found_at.month:
                        year = current_year - 1
                    else:
                        year = current_year

                    posted_time = datetime.strptime(time_str, "%H:%M").time()
                    posted_datetime = datetime(year, month, day, posted_time.hour, posted_time.minute)
                    return timezone.make_aware(posted_datetime)

        return None

    except Exception as e:
        add_to_console(f"Error parsing date '{posted_date_str}': {e}")
        return None


@register.filter
def abs_value(value):
    """Возвращает абсолютное значение числа."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter
def replace(value, arg):
    """
    Заменяет подстроку в строке.
    Использование: {{ value|replace:"old,new" }}
    """
    if not value or not arg:
        return value

    try:
        old, new = arg.split(',')
        return str(value).replace(old, new)
    except (ValueError, AttributeError):
        return value

@register.filter
def search_time_display(found_at, posted_date_str):
    """Отображает время, за которое было найдено объявление"""
    if not posted_date_str:
        return "неизвестно"

    posted_datetime = parse_avito_date(posted_date_str, found_at)
    if not posted_datetime:
        return "неизвестно"

    try:
        search_time = found_at - posted_datetime
        return format_timedelta(search_time)
    except Exception as e:
        add_to_console(f"Error calculating time difference: {e}")
        return "неизвестно"


def format_timedelta(td):
    """Форматирует timedelta в читаемый вид"""
    total_seconds = int(td.total_seconds())

    if total_seconds < 0:
        return "0м"  # Если время отрицательное

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours} часов {minutes} минут"
    elif minutes > 0:
        return f"{minutes} минут"
    else:
        return f"{seconds} секунд"


@register.filter
def cut(value, arg):
    """Удаляет подстроку из строки"""
    try:
        return value.replace(arg, '')
    except (AttributeError, TypeError):
        return value


# Новые функции для фильтрации и сортировки
@register.simple_tag(takes_context=True)
def modify_query(context, **kwargs):
    """
    Модифицирует текущий query string, добавляя или изменяя параметры
    Использование: {% modify_query page=1 sort_by='-price' %}
    """
    request = context.get('request')
    if not request:
        return ''

    query_dict = request.GET.copy()

    for key, value in kwargs.items():
        if value is None:
            if key in query_dict:
                del query_dict[key]
        else:
            query_dict[key] = value

    return query_dict.urlencode()


@register.filter
def get_item(dictionary, key):
    """Получает значение из словаря по ключу"""
    return dictionary.get(key)


@register.filter
def add_url_param(url, param):
    """Добавляет параметр к URL"""
    if '?' in url:
        return f"{url}&{param}"
    else:
        return f"{url}?{param}"


@register.filter
def is_active_filter(filters, filter_type):
    """Проверяет, активен ли фильтр"""
    if filter_type == 'category' and filters.get('category') and filters.get('category') != 'all':
        return True
    elif filter_type == 'price' and (filters.get('price_min') or filters.get('price_max')):
        return True
    elif filter_type == 'seller' and filters.get('seller_type'):
        return True
    elif filter_type == 'profitable' and filters.get('profitable_only'):
        return True
    return False


@register.filter
def get_sort_display_name(sort_by):
    """Возвращает читаемое название для сортировки"""
    sort_names = {
        '-found_at': 'Сначала новые',
        'price': 'Цена по возрастанию',
        '-price': 'Цена по убыванию',
        'category': 'Категория А-Я',
        '-category': 'Категория Я-А',
        '-posted_date': 'Сначала свежие объявления'
    }
    return sort_names.get(sort_by, 'Сначала новые')


@register.filter
def can_sort_by_field(field_name, found_items):
    """Проверяет, можно ли сортировать по указанному полю"""
    if not found_items or not hasattr(found_items, 'first') or not found_items.first():
        return False

    first_item = found_items.first()
    return hasattr(first_item, field_name)


@register.simple_tag(takes_context=True)
def current_url_without_params(context, *params_to_remove):
    """Возвращает текущий URL без указанных параметров"""
    request = context.get('request')
    if not request:
        return ''

    query_dict = request.GET.copy()
    for param in params_to_remove:
        if param in query_dict:
            del query_dict[param]

    if query_dict:
        return f"?{query_dict.urlencode()}"
    else:
        return ""


@register.filter
def truncate_words_custom(text, word_count=20):
    """Обрезает текст до указанного количества слов"""
    if not text:
        return ''

    words = text.split()
    if len(words) <= word_count:
        return text

    return ' '.join(words[:word_count]) + '...'


@register.filter
def format_price(price):
    """Форматирует цену с разделителями тысяч"""
    try:
        return f"{int(price):,}".replace(',', ' ')
    except (ValueError, TypeError):
        return price

@register.filter
def split(value, arg):
    """Разделяет строку по разделителю"""
    return value.split(arg)

@register.simple_tag
def get_total_items(user):
    """Возвращает общее количество ВСЕХ товаров пользователя"""
    from apps.website.models import FoundItem
    return FoundItem.objects.filter(search_query__user=user).count()