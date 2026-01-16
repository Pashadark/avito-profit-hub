# notifications/middleware.py
from .services import ToastNotificationSystem


class ToastNotificationMiddleware:
    """Middleware для обработки toast уведомлений"""

    def __init__(self, get_response):
        self.get_response = get_response
        print("🎯 ToastNotificationMiddleware initialized")

    def __call__(self, request):
        print(f"🎯 Middleware called for: {request.path}")

        # Добавляем уведомления в объект запроса
        try:
            request.toast_notifications = ToastNotificationSystem.get_all(request)
            print(f"🎯 Added {len(request.toast_notifications)} notifications to request")
        except Exception as e:
            print(f"❌ Error adding notifications to request: {str(e)}")
            request.toast_notifications = []

        response = self.get_response(request)

        # Очищаем уведомления после отображения
        try:
            if (request.method == 'GET' and
                    not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' and
                    not request.path.startswith('/admin/')):
                count_before = len(ToastNotificationSystem.get_all(request))
                ToastNotificationSystem.clear_all(request)
                count_after = len(ToastNotificationSystem.get_all(request))

                print(f"🎯 Cleared notifications: {count_before} -> {count_after}")
        except Exception as e:
            print(f"❌ Error clearing notifications: {str(e)}")

        return response