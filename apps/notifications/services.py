# notifications/services.py
from django.contrib import messages
from django.utils import timezone


class ToastNotificationSystem:

    @staticmethod
    def _get_session_key(request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f'toast_notifications_{request.user.id}'
        return 'toast_notifications_anonymous'

    @classmethod
    def success(cls, request, message, title='', **kwargs):
        return cls._add_toast(request, 'success', message, title, **kwargs)

    @classmethod
    def info(cls, request, message, title='', **kwargs):
        return cls._add_toast(request, 'info', message, title, **kwargs)

    @classmethod
    def warning(cls, request, message, title='', **kwargs):
        return cls._add_toast(request, 'warning', message, title, **kwargs)

    @classmethod
    def error(cls, request, message, title='', **kwargs):
        return cls._add_toast(request, 'error', message, title, **kwargs)

    @classmethod
    def _add_toast(cls, request, notification_type, message, title='', **kwargs):
        toast_data = {
            'type': notification_type,
            'message': str(message),
            'title': str(title),
            'position': 'toast-top-right',
            'timeOut': 5000,
            'closeButton': True,
            'progressBar': True,
            'timestamp': timezone.now().isoformat()
        }

        if hasattr(request, 'session'):
            try:
                session_key = cls._get_session_key(request)
                if session_key not in request.session:
                    request.session[session_key] = []

                notifications = request.session[session_key]
                if len(notifications) >= 10:
                    notifications.pop(0)

                notifications.append(toast_data)
                request.session[session_key] = notifications
                request.session.modified = True
            except:
                pass

        # Django messages
        full_message = f"{title}: {message}" if title else message
        if notification_type == 'success':
            messages.success(request, full_message)
        elif notification_type == 'info':
            messages.info(request, full_message)
        elif notification_type == 'warning':
            messages.warning(request, full_message)
        elif notification_type == 'error':
            messages.error(request, full_message)

        return toast_data

    @classmethod
    def get_all(cls, request):
        if hasattr(request, 'session'):
            try:
                session_key = cls._get_session_key(request)
                return request.session.get(session_key, [])
            except:
                return []
        return []

    @classmethod
    def clear_all(cls, request):
        if hasattr(request, 'session'):
            try:
                session_key = cls._get_session_key(request)
                if session_key in request.session:
                    del request.session[session_key]
                    request.session.modified = True
            except:
                pass


toast = ToastNotificationSystem()