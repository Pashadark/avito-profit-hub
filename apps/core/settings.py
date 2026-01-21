# apps/core/settings.py - Avito Profit Hub
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ============================================
# ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ============================================
load_dotenv()

# ============================================
# БАЗОВЫЕ НАСТРОЙКИ ПРОЕКТА
# ============================================
# ИСПРАВЛЕНО: Правильный путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ДОБАВИЛ: Добавляем apps в путь Python
sys.path.insert(0, str(BASE_DIR))

# ============================================
# БЕЗОПАСНОСТЬ DJANGO
# ============================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-development-only')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ============================================
# УСТАНОВЛЕННЫЕ ПРИЛОЖЕНИЯ
# ============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Сторонние приложения
    'rest_framework',
    'corsheaders',

    # Собственные приложения проекта
    'apps.website',
    'apps.parsing',
    'apps.bot',
    'apps.notifications',
]

# ============================================
# ПРОМЕЖУТОЧНОЕ ПО (MIDDLEWARE)
# ============================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.notifications.middleware.ToastNotificationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.website.middleware.ConsoleCaptureMiddleware',
    'apps.core.middleware.request_logger.RequestLoggingMiddleware',
    'apps.core.middleware.request_logger.StaticFilesLoggingMiddleware',
    'apps.website.middleware.UserActivityMiddleware',
    'apps.website.middleware.SubscriptionAccessMiddleware',
    'apps.website.middleware.request_timing.RequestTimingMiddleware'
]

# ============================================
# НАСТРОЙКИ URL
# ============================================
ROOT_URLCONF = 'apps.core.urls'

# ============================================
# НАСТРОЙКИ ШАБЛОНОВ
# ============================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'apps/website/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.website.context_processors.user_profile',
            ],
        },
    },
]

# ============================================
# WSGI ПРИЛОЖЕНИЕ
# ============================================
WSGI_APPLICATION = 'apps.core.wsgi.application'

# ============================================
# НАСТРОЙКИ БАЗЫ ДАННЫХ - POSTGRESQL
# ============================================
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'site_hub'),
        'USER': os.getenv('DB_USER', 'pashadark'),
        'PASSWORD': os.getenv('DB_PASSWORD', '12344321'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60')),
        'ATOMIC_REQUESTS': os.getenv('DB_ATOMIC_REQUESTS', 'True') == 'True',
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# ============================================
# НАСТРОЙКИ ПОДПИСОК
# ============================================
SUBSCRIPTION_SETTINGS = {
    'GRACE_PERIOD_DAYS': 3,
    'LOW_BALANCE_WARNING_DAYS': 5,
    'AUTO_RENEW': True,
}

# ============================================
# НАСТРОЙКИ УВЕДОМЛЕНИЙ
# ============================================
NOTIFICATIONS_CONFIG = {
    'DEFAULT_POSITION': 'toast-top-right',
    'SUCCESS_DURATION': 4000,
    'ERROR_DURATION': 7000,
    'ENABLE_PROGRESS_BAR': True,
    'ENABLE_CLOSE_BUTTON': True,
}

# ============================================
# НАСТРОЙКИ БЭКАПОВ
# ============================================
BACKUP_DIR = BASE_DIR / 'database_backups'
MAX_BACKUP_DAYS = 7

# ============================================
# ВАЛИДАТОРЫ ПАРОЛЕЙ
# ============================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================
# МЕЖДУНАРОДНЫЕ НАСТРОЙКИ
# ============================================
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# ============================================
# НАСТРОЙКИ СТАТИЧЕСКИХ ФАЙЛОВ
# ============================================
# ДЛЯ РАЗРАБОТКИ - static файлы из разных мест
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Куда collectstatic собирает статику
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ============================================
# НАСТРОЙКИ МОДЕЛЕЙ
# ============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# НАСТРОЙКИ АУТЕНТИФИКАЦИИ
# ============================================
LOGIN_REDIRECT_URL = 'website:dashboard'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'

# ============================================
# EXTERNAL API KEYS
# ============================================
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
ADMIN_TELEGRAM_ID = os.getenv('ADMIN_TELEGRAM_ID', '')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
AVITO_UPDATE_INTERVAL = int(os.getenv('AVITO_UPDATE_INTERVAL', '3600'))
AVITO_SEARCH_DELAY = int(os.getenv('AVITO_SEARCH_DELAY', '2'))
WEATHER_UPDATE_INTERVAL = int(os.getenv('WEATHER_UPDATE_INTERVAL', '600'))

# ============================================
# РОССИЙСКИЕ ГОРОДА ДЛЯ ПОГОДЫ
# ============================================
RUSSIAN_CITIES = [
    os.getenv('RUSSIAN_CITIES_MOSCOW', 'Москва'),
    os.getenv('RUSSIAN_CITIES_SAINT_PETERSBURG', 'Санкт-Петербург'),
    os.getenv('RUSSIAN_CITIES_NOVOSIBIRSK', 'Новосибирск'),
    os.getenv('RUSSIAN_CITIES_YEKATERINBURG', 'Екатеринбург'),
    os.getenv('RUSSIAN_CITIES_KAZAN', 'Казань'),
    os.getenv('RUSSIAN_CITIES_NIZHNY_NOVGOROD', 'Нижний Новгород'),
]

# ============================================
# НАСТРОЙКИ СЕССИЙ
# ============================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_NAME = 'sessionid_parser'
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# ============================================
# НАСТРОЙКИ CSRF
# ============================================
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_AGE = 31449600
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.3.15:8000',
]

# ============================================
# CORS НАСТРОЙКИ
# ============================================
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True') == 'True'
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================
# НАСТРОЙКИ DJANGO REST FRAMEWORK
# ============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ БЕЗОПАСНОСТИ
# ============================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ============================================
# ОБРАБОТЧИКИ ОШИБОК
# ============================================
handler400 = 'apps.core.views.bad_request'
handler403 = 'apps.core.views.permission_denied'
handler404 = 'apps.core.views.page_not_found'
handler500 = 'apps.core.views.server_error'

# ============================================
# НАСТРОЙКИ ДЛЯ РАЗРАБОТКИ
# ============================================
if DEBUG:
    SILENCED_SYSTEM_CHECKS = [
        'security.W001',
        'security.W002',
        'security.W003',
        'security.W004',
        'security.W008',
        'security.W009',
        'security.W016',
    ]

# ============================================
# НАСТРОЙКИ БЕЗОПАСНОСТИ ДЛЯ ДИНАМИЧЕСКОЙ ТАБЛИЦЫ
# ============================================
SECURITY_SETTINGS = {
    'TABLE_UPDATE_MIN_INTERVAL': 15,
    'TABLE_UPDATE_MAX_INTERVAL': 300,
    'MAX_TABLE_ITEMS': 10,
    'RATE_LIMIT_PER_MINUTE': 30,
    'MAX_ERROR_COUNT': 5,
}

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ CSRF НАСТРОЙКИ
# ============================================
CSRF_FAILURE_VIEW = 'apps.core.views.csrf_failure'

# ============================================
# НАСТРОЙКИ REST FRAMEWORK С РЕЙТ-ЛИМИТИНГОМ
# ============================================
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '30/minute',
    }
})

# ============================================
# POSTGRESQL СПЕЦИФИЧНЫЕ НАСТРОЙКИ
# ============================================
POSTGRESQL_SETTINGS = {
    'ENABLE_JSONB_INDEXING': os.getenv('POSTGRES_ENABLE_JSONB_INDEXING', 'True') == 'True',
    'ENABLE_TRIGRAM_SEARCH': os.getenv('POSTGRES_ENABLE_TRIGRAM_SEARCH', 'True') == 'True',
    'ENABLE_PARTIAL_INDEXES': True,
    'CONNECTION_POOL_SIZE': 5,
    'STATEMENT_TIMEOUT': int(os.getenv('POSTGRES_STATEMENT_TIMEOUT', '30000')),
}

# ============================================
# НАСТРОЙКИ МЕДИА ФАЙЛОВ
# ============================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================
# ПРОВЕРКА ПОДКЛЮЧЕНИЯ К POSTGRESQL ПРИ СТАРТЕ
# ============================================
def check_postgresql_connection():
    """Проверка подключения к PostgreSQL при старте Django"""
    try:
        from django.db import connections
        from django.db.utils import OperationalError
        import time

        if DEBUG:
            print("🔍 Проверка подключения к PostgreSQL...")

        start_time = time.time()
        conn = connections['default']
        conn.ensure_connection()
        end_time = time.time()

        if DEBUG:
            # Получаем настройки из .env для безопасного логирования
            db_name = os.getenv('DB_NAME', 'site_hub')
            db_user = os.getenv('DB_USER', 'pashadark')

            print(f"✅ PostgreSQL подключен успешно! Время: {round((end_time - start_time) * 1000)}ms")
            print(f"🗄️ База данных: {db_name}")
            print(f"👤 Пользователь: {db_user}")
            print(f"🌐 Хост: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}")

            # Проверка таблиц
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                table_count = cursor.fetchone()[0]
                print(f"📊 Таблиц в базе: {table_count}")

        return True

    except OperationalError as e:
        if DEBUG:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            print("\n🔧  Устранение неполадок:")
            print("   1. Проверьте, запущен ли PostgreSQL сервер:")
            print("      Windows: services.msc → PostgreSQL")
            print("      Linux: sudo systemctl status postgresql")
            print("      Mac: brew services list")
            print("   2. Проверьте настройки в .env файле:")
            print(f"      DB_NAME={os.getenv('DB_NAME', 'site_hub')}")
            print(f"      DB_USER={os.getenv('DB_USER', 'pashadark')}")
            print("      DB_PASSWORD=********")
            print(f"      DB_HOST={os.getenv('DB_HOST', 'localhost')}")
            print(f"      DB_PORT={os.getenv('DB_PORT', '5432')}")
            print("   3. Проверьте доступность порта 5432:")
            print("      telnet localhost 5432")
        return False
    except Exception as e:
        if DEBUG:
            print(f"⚠️ Неизвестная ошибка при проверке PostgreSQL: {e}")
        return False
