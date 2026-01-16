from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views  # Импортируем views из core


def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        # ИЗМЕНИЛ: dashboard → website
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except ImportError:
        # Если модуль не найден, используем простой вывод
        print(f"[SAFE_LOG] {message}")
    except Exception as e:
        # Другие ошибки
        print(f"[SAFE_LOG ERROR] {message} - {e}")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.website.urls')),  # Django сам возьмет namespace из app_name
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Маршруты для тестирования ошибок (только в режиме DEBUG)
from django.conf import settings
if settings.DEBUG:
    urlpatterns += [
        path('test/400/', views.bad_request),
        path('test/403/', views.permission_denied),
        path('test/404/', views.page_not_found),
        path('test/500/', views.server_error),
        # Дополнительный маршрут для реальной 500 ошибки
        path('test/500-real/', views.test_500_error),
    ]