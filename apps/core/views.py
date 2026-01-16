from django.shortcuts import render
from django.conf import settings

def bad_request(request, exception=None):
    context = {
        'title': 'Неверный запрос - 400',
        'error_code': 400
    }
    return render(request, 'errors/400.html', context, status=400)

def permission_denied(request, exception=None):
    context = {
        'title': 'Доступ запрещен - 403',
        'error_code': 403
    }
    return render(request, 'errors/403.html', context, status=403)

def page_not_found(request, exception=None):
    context = {
        'title': 'Страница не найдена - 404',
        'error_code': 404,
        'request_path': request.path
    }
    return render(request, 'errors/404.html', context, status=404)

def server_error(request):
    context = {
        'title': 'Ошибка сервера - 500',
        'error_code': 500,
        'debug': settings.DEBUG
    }
    return render(request, 'errors/500.html', context, status=500)

# Функция для тестирования реальной 500 ошибки (только для разработки)
def test_500_error(request):
    """Тестовая функция для генерации реальной 500 ошибки"""
    raise Exception("Это тестовая 500 ошибка для проверки обработки исключений")


def csrf_failure(request, reason=""):
    """Кастомная страница для ошибок CSRF"""
    from django.http import JsonResponse

    context = {
        'title': 'Ошибка безопасности - 403',
        'message': 'Недействительный CSRF токен. Пожалуйста, обновите страницу.',
        'reason': reason,
        'error_code': 403
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Для AJAX запросов возвращаем JSON
        return JsonResponse({
            'status': 'error',
            'message': 'CSRF verification failed. Please refresh the page.',
            'reason': reason
        }, status=403)
    else:
        # Для обычных запросов возвращаем HTML страницу
        return render(request, 'errors/403_csrf.html', context, status=403)