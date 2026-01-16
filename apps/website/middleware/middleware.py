import sys
import time
from io import StringIO
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.core.cache import cache
from django.utils import timezone
from apps.website.console_manager import add_to_console


class ConsoleCaptureMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.console_output = StringIO()

    def __call__(self, request):
        # Сохраняем оригинальный stdout
        old_stdout = sys.stdout

        try:
            # Перенаправляем stdout в наш StringIO
            sys.stdout = self.console_output

            # Обрабатываем запрос
            response = self.get_response(request)

            return response

        finally:
            # Восстанавливаем оригинальный stdout
            sys.stdout = old_stdout

            # Получаем вывод и очищаем буфер
            captured_output = self.console_output.getvalue()
            self.console_output.seek(0)
            self.console_output.truncate(0)

            # Фильтруем вывод - добавляем только непустые строки
            if captured_output.strip():
                # Разделяем на строки и обрабатываем каждую
                lines = captured_output.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('[') and not 'Middleware' in line:
                        # Добавляем в консоль с пометкой, что это из stdout
                        add_to_console(f"[STDOUT] {line.strip()}", log_to_console=False)


class UserActivityMiddleware:
    """
    Middleware для отслеживания активности пользователей
    и определения онлайн-статуса
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Отслеживаем активность только для аутентифицированных пользователей
        if request.user.is_authenticated:
            user = request.user

            # Ключ для кэша активности пользователя
            activity_key = f'user_activity_{user.id}'
            status_key = f'user_online_{user.id}'

            # Обновляем время последней активности
            current_time = timezone.now()
            cache.set(activity_key, current_time, 300)  # 5 минут

            # Обновляем онлайн статус
            cache.set(status_key, True, 300)  # 5 минут

            # Логируем активность (опционально)
            if settings.DEBUG:
                print(f"🟢 User activity: {user.username} at {current_time}")

        return response


class SubscriptionAccessMiddleware:
    """
    Middleware для проверки доступа к парсеру
    на основе активной подписки и баланса (новый стиль)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Пропускаем статические файлы, админку и публичные маршруты
        public_paths = [
            '/admin/', '/static/', '/media/', '/login/', '/register/',
            '/accounts/login/', '/logout/', '/subscription/', '/balance/',
            '/payment/', '/api/auth/', '/favicon.ico'
        ]

        if any(request.path.startswith(path) for path in public_paths):
            return self.get_response(request)

        # Пропускаем неаутентифицированных пользователей
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Проверяем доступ только к защищенным маршрутам парсера
        parser_paths = [
            '/parser/', '/start-parser', '/api/parser',
            '/found-items/', '/parser-settings/', '/api/start-parser'
        ]

        is_parser_route = any(request.path.startswith(path) for path in parser_paths)

        if is_parser_route:
            try:
                from apps.website.utils.subscription_utils import SubscriptionManager

                can_use, message = SubscriptionManager.can_user_use_parser(request.user)

                if not can_use:
                    # Для AJAX запросов возвращаем JSON
                    if request.headers.get(
                            'X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                        return JsonResponse({
                            'success': False,
                            'error': message,
                            'redirect_url': '/subscription/'
                        }, status=402)  # Payment Required
                    else:
                        # Для обычных запросов редирект на страницу подписки
                        return redirect('/subscription/')

            except ImportError:
                # Если утилиты подписок еще не доступны, пропускаем проверку
                pass
            except Exception as e:
                # В случае ошибки логируем и пропускаем проверку
                add_to_console(f"[SUBSCRIPTION MIDDLEWARE ERROR] {str(e)}")

        return self.get_response(request)