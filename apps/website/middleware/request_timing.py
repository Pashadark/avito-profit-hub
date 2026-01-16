import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('user.actions')


class RequestTimingMiddleware(MiddlewareMixin):
    """Middleware для отслеживания времени выполнения запросов"""

    # Словарь для определения названий страниц по их путям
    PAGE_NAMES = {
        # Основные страницы
        '/': 'Главная страница',
        '/dashboard/': 'Дашборд',
        '/profile/': 'Профиль пользователя',
        '/parser-settings/': 'Настройки парсера',
        '/debug-settings/': 'Настройки отладки',
        '/products/': 'Товары',
        '/found-items/': 'Найденные товары',
        '/deals/': 'Сделки',
        '/help/': 'Помощь',
        '/subscription/': 'Подписка',
        '/balance/': 'Баланс',
        '/payment/': 'Оплата',
        '/login/': 'Вход в систему',
        '/register/': 'Регистрация',
        '/logout/': 'Выход из системы',
        '/todo-kanban/': 'TODO Канбан',
        '/vision-statistics/': 'Статистика Vision',

        # API эндпоинты
        '/api/parser-status/': 'Статус парсера',
        '/api/admin-logs/': 'Логи администратора',
        '/api/database-stats/': 'Статистика БД',
        '/api/database-info/': 'Информация о БД',
        '/api/parser-stats/': 'Статистика парсера',
        '/api/list-backups/': 'Список бэкапов',
        '/api/vision-stats/': 'Статистика Vision',
        '/api/console-update/': 'Обновление консоли',
        '/api/performance-metrics/': 'Метрики производительности',
        '/api/system-health/': 'Здоровье системы',
        '/api/user-ml-stats/': 'ML статистика пользователя',

        # Парсер
        '/start-parser/': 'Запуск парсера',
        '/stop-parser/': 'Остановка парсера',
        '/parser-status/': 'Статус парсера',
    }

    def _get_page_name(self, path):
        """Получает понятное название страницы по пути"""
        # Ищем точное совпадение
        if path in self.PAGE_NAMES:
            return self.PAGE_NAMES[path]

        # Ищем частичное совпадение
        for key, value in self.PAGE_NAMES.items():
            if path.startswith(key):
                return value

        # Определяем тип по префиксу
        if path.startswith('/api/'):
            return 'API запрос'
        elif path.startswith('/admin/'):
            return 'Админ панель'
        elif path.startswith('/parser/'):
            return 'Парсер'
        elif path.startswith('/static/'):
            return 'Статический файл'
        elif path.startswith('/media/'):
            return 'Медиа файл'
        else:
            return 'Страница'

    def _get_action_type(self, path, method):
        """Определяет тип действия"""
        if path.startswith('/api/'):
            return '📡 API ВЫЗОВ'
        elif '/profile' in path:
            return '👤 ПРОФИЛЬ'
        elif '/parser' in path:
            return '⚙️ ПАРСЕР'
        elif '/admin' in path:
            return '⚙️ АДМИН'
        elif method == 'GET':
            return '🌐 ПРОСМОТР'
        elif method == 'POST':
            return '📝 СОЗДАНИЕ'
        elif method == 'PUT':
            return '🔄 ОБНОВЛЕНИЕ'
        elif method == 'DELETE':
            return '🗑️ УДАЛЕНИЕ'
        else:
            return '🌐 ДЕЙСТВИЕ'

    def _get_client_ip(self, request):
        """Получаем IP клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _get_device_type(self, user_agent):
        """Определяет тип устройства по User-Agent"""
        ua = user_agent.lower() if user_agent else ''
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            return '📱 Мобильный'
        elif 'tablet' in ua or 'ipad' in ua:
            return '📟 Планшет'
        elif 'bot' in ua or 'crawler' in ua or 'spider' in ua:
            return '🤖 Бот'
        else:
            return '💻 ПК'

    def process_request(self, request):
        """Засекаем время начала обработки запроса"""
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        """Логируем время выполнения запроса"""
        if hasattr(request, 'start_time'):
            elapsed = time.time() - request.start_time

            # Форматируем время
            if elapsed < 0.001:
                time_str = f"{elapsed * 1000:.0f}ms"
            elif elapsed < 1:
                time_str = f"{elapsed * 1000:.1f}ms"
            else:
                time_str = f"{elapsed:.2f}s"

            # Информация о пользователе
            user = request.user.username if request.user.is_authenticated else 'Аноним'
            method = request.method
            path = request.path

            # Определяем тип действия и название страницы
            action_type = self._get_action_type(path, method)
            page_name = self._get_page_name(path)

            # IP и устройство
            ip = self._get_client_ip(request)
            device = self._get_device_type(request.META.get('HTTP_USER_AGENT', 'Unknown'))

            # Статус код
            status = response.status_code

            # Определяем эмодзи по статусу
            if 200 <= status < 300:
                emoji = '✅'
            elif 300 <= status < 400:
                emoji = '🔄'
            elif 400 <= status < 500:
                emoji = '⚠️'
            else:
                emoji = '❌'

            # Логируем одно информативное сообщение
            logger.info(
                f"{emoji} {action_type} | Пользователь: {user} | Действие: {page_name} | Время: {time_str} | IP: {ip} | Устройство: {device}")

            # Второе сообщение с техническими деталями (для отладки, можно закомментировать)
            # logger.info(f"{emoji} {method} {path} → {status} за {time_str}")

        return response