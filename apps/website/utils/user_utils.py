from django.core.cache import cache
from django.utils import timezone


def is_user_online(user):
    """
    Проверяет, онлайн ли пользователь
    Считается онлайн, если была активность в последние 5 минут
    """
    if not user or not user.is_authenticated:
        return False

    cache_key = f'user_online_{user.id}'
    return cache.get(cache_key, False)


def get_last_activity(user):
    """
    Возвращает время последней активности пользователя
    """
    if not user or not user.is_authenticated:
        return None

    cache_key = f'user_activity_{user.id}'
    last_activity = cache.get(cache_key)

    if last_activity:
        return last_activity
    return user.last_login


def get_activity_display(user):
    """
    Возвращает текстовое представление времени активности
    """
    last_activity = get_last_activity(user)

    if not last_activity:
        return "Никогда"

    time_diff = timezone.now() - last_activity
    minutes = int(time_diff.total_seconds() / 60)

    if minutes < 1:
        return "Только что"
    elif minutes < 60:
        return f"{minutes} минут назад"
    elif minutes < 1440:  # 24 часа
        hours = minutes // 60
        return f"{hours} часов назад"
    else:
        days = minutes // 1440
        return f"{days} дней назад"