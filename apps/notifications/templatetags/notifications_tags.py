from django import template
from django.utils.html import mark_safe
import json
from django.contrib.messages import get_messages

register = template.Library()


@register.simple_tag(takes_context=True)
def load_notifications_css(context):
    """Загружает CSS для уведомлений (новая система)"""
    return mark_safe('<link rel="stylesheet" href="/static/notifications/css/notifications.css">')


@register.simple_tag(takes_context=True)
def load_notifications_js(context):
    """Загружает JS для уведомлений (новая система)"""
    return mark_safe('<script src="/static/notifications/js/notifications.js"></script>')


@register.inclusion_tag('notifications/toast_container.html', takes_context=True)
def render_toast_container(context):
    """Рендерит контейнер для toast уведомлений с новой системой"""
    request = context.get('request')
    notifications_data = []

    if not request:
        return {'notifications_json': '[]'}

    # Из сессии (ваша система)
    try:
        from ..services import ToastNotificationSystem
        notifications_data.extend(ToastNotificationSystem.get_all(request))
    except Exception as e:
        print(f"Error getting session notifications: {e}")

    # Из Django messages
    try:
        for message in get_messages(request):
            level_map = {
                20: 'info',
                25: 'success',
                30: 'warning',
                40: 'error',
            }
            notification_type = level_map.get(message.level, 'info')

            # Иконки по типу
            icon_map = {
                'success': 'ri-checkbox-circle-fill text-success',
                'error': 'ri-error-warning-fill text-danger',
                'warning': 'ri-alert-fill text-warning',
                'info': 'ri-information-fill text-info'
            }

            icon_class = icon_map.get(notification_type, 'ri-information-fill text-info')

            notifications_data.append({
                'type': notification_type,
                'message': str(message),
                'title': 'Уведомление',
                'icon': icon_class,
                'position': 'toast-top-right',
                'timeOut': 5000,
                'closeButton': True,
                'progressBar': True,
                'template': 'notifications'  # Флаг для новой системы
            })
    except Exception as e:
        print(f"Error getting Django messages: {e}")

    try:
        notifications_json = json.dumps(notifications_data, ensure_ascii=False)
    except:
        notifications_json = '[]'

    return {
        'notifications_json': notifications_json,
        'notifications': notifications_data,
        'request': request
    }


@register.filter
def notification_class(type):
    """Конвертирует тип уведомления в CSS класс"""
    class_map = {
        'success': 'notification-success',
        'error': 'notification-error',
        'warning': 'notification-warning',
        'info': 'notification-info',
        'danger': 'notification-error'
    }
    return class_map.get(type, 'notification-info')


@register.filter
def notification_icon(type):
    """Возвращает иконку для типа уведомления"""
    icon_map = {
        'success': 'ri-checkbox-circle-fill text-success',
        'error': 'ri-error-warning-fill text-danger',
        'warning': 'ri-alert-fill text-warning',
        'info': 'ri-information-fill text-info',
        'danger': 'ri-error-warning-fill text-danger'
    }
    return icon_map.get(type, 'ri-information-fill text-info')


@register.filter
def notification_title(type):
    """Возвращает заголовок по умолчанию для типа уведомления"""
    title_map = {
        'success': 'Успешно',
        'error': 'Ошибка',
        'warning': 'Внимание',
        'info': 'Информация',
        'danger': 'Ошибка'
    }
    return title_map.get(type, 'Уведомление')