import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('request')


class RequestLoggingMiddleware:
    """
    🔥 УЛУЧШЕННЫЙ МИДЛВАР ДЛЯ ЛОГИРОВАНИЯ ЗАПРОСОВ
    ✅ В стиле парсера Avito
    ✅ С отслеживанием действий пользователей
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.user_actions_logger = logging.getLogger('user.actions')

    def __call__(self, request):
        # Обработка запроса
        response = self.process_request(request)
        if response:
            return response

        # Получаем ответ от следующего middleware/view
        response = self.get_response(request)

        # Обработка ответа
        response = self.process_response(request, response)
        return response

    def process_request(self, request):
        """Начало обработки запроса"""
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        """Обработка ответа и логирование"""
        if hasattr(request, 'start_time'):
            try:
                duration = time.time() - request.start_time

                # Получаем информацию о запросе
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
                device_info = self._analyze_user_agent(user_agent)

                # 🔥 ЛОГИРОВАНИЕ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ В СТИЛЕ ПАРСЕРА
                user_action = self._log_user_action_avito_style(request, response, ip_address, device_info, duration)

                # Если это не действие пользователя, логируем обычный запрос
                if not user_action:
                    # Определяем эмодзи для статуса
                    status_emoji = self._get_status_emoji(response.status_code)

                    # Логируем информацию о запросе
                    log_message = (
                        f"🌐 {request.method} {request.path} | "
                        f"Status: {status_emoji} {response.status_code} | "
                        f"Time: {duration:.3f}s | "
                        f"IP: {ip_address} | "
                        f"Device: {device_info['device_type']} | "
                        f"Browser: {device_info['browser']} | "
                        f"OS: {device_info['os']}"
                    )

                    # Дополнительная информация для медленных запросов
                    if duration > 1.0:
                        log_message += f" 🐌 МЕДЛЕННЫЙ ЗАПРОС!"
                    elif duration > 0.5:
                        log_message += f" ⚠️ ВНИМАНИЕ"

                    logger.info(log_message)

            except Exception as e:
                # Логируем ошибку, но не прерываем выполнение
                logger.error(f"❌ Ошибка логирования запроса: {e}")

        return response

    def _log_user_action_avito_style(self, request, response, ip_address, device_info, duration):
        """🔍 ЛОГИРОВАНИЕ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ В СТИЛЕ ПАРСЕРА AVITO"""
        try:
            path = request.path
            method = request.method

            # Определяем тип действия пользователя
            action_info = self._get_user_action_info(request, response)

            if action_info:
                # Получаем информацию о пользователе
                user_info = self._get_user_info(request)

                # 🔥 ФОРМАТИРОВАНИЕ В СТИЛЕ ПАРСЕРА AVITO
                action_message = (
                    f"✅ {action_info['type']} | "
                    f"Пользователь: {user_info} | "
                    f"Действие: {action_info['action']} | "
                    f"Время: {duration:.3f}s | "
                    f"IP: {ip_address} | "
                    f"Устройство: {device_info['device_type']}"
                )

                # Логируем действие пользователя
                self.user_actions_logger.info(action_message)
                return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка логирования действия пользователя: {e}")

        return False

    def _get_user_action_info(self, request, response):
        """🔍 ОПРЕДЕЛЕНИЕ ИНФОРМАЦИИ О ДЕЙСТВИИ ПОЛЬЗОВАТЕЛЯ"""
        path = request.path
        method = request.method

        # 🔥 АВТОРИЗАЦИЯ И СЕССИИ
        if any(auth_path in path for auth_path in ['/login/', '/logout/', '/signin/', '/signout/']):
            if 'login' in path or 'signin' in path:
                return {"type": "👤 АУТЕНТИФИКАЦИЯ", "action": "Вход в систему"}
            elif 'logout' in path or 'signout' in path:
                return {"type": "👤 СЕССИЯ", "action": "Выход из системы"}

        # 🔥 АДМИНИСТРИРОВАНИЕ
        elif '/admin/' in path:
            if method == 'GET':
                return {"type": "⚙️ АДМИН ПАНЕЛЬ", "action": "Просмотр админки"}
            elif method == 'POST':
                return {"type": "⚙️ АДМИН ДЕЙСТВИЕ", "action": "Изменение данных"}

        # 🔥 ГЛАВНЫЕ СТРАНИЦЫ
        elif method == 'GET' and response.status_code == 200:
            if path == '/':
                return {"type": "🏠 ГЛАВНАЯ", "action": "Просмотр главной страницы"}
            elif '/search/' in path:
                return {"type": "🔍 ПОИСК", "action": "Выполнение поиска"}
            elif '/deals/' in path:
                return {"type": "💰 СДЕЛКИ", "action": "Просмотр сделок"}
            elif '/todo/' in path:
                return {"type": "📝 ЗАДАЧИ", "action": "Работа с задачами"}
            elif '/settings/' in path:
                return {"type": "⚙️ НАСТРОЙКИ", "action": "Просмотр настроек"}
            elif '/dashboard/' in path:
                return {"type": "📊 ДАШБОРД", "action": "Просмотр дашборда"}
            elif '/profile/' in path:
                return {"type": "👤 ПРОФИЛЬ", "action": "Просмотр профиля"}
            elif '/debug/' in path:
                return {"type": "🐛 ОТЛАДКА", "action": "Просмотр отладочной информации"}
            elif '/parser/' in path:
                return {"type": "🚀 ПАРСЕР", "action": "Управление парсером"}

        # 🔥 ДЕЙСТВИЯ С ДАННЫМИ
        elif method == 'POST':
            if '/api/' in path:
                if '/start-parser/' in path:
                    return {"type": "🚀 ЗАПУСК ПАРСЕРА", "action": "Запуск парсера"}
                elif '/stop-parser/' in path:
                    return {"type": "🛑 ОСТАНОВКА ПАРСЕРА", "action": "Остановка парсера"}
                elif '/update-settings/' in path:
                    return {"type": "⚙️ ОБНОВЛЕНИЕ НАСТРОЕК", "action": "Изменение настроек"}
                else:
                    return {"type": "📡 API ВЫЗОВ", "action": "Выполнение API запроса"}

            elif any(action_path in path for action_path in ['/create/', '/add/', '/new/']):
                return {"type": "➕ СОЗДАНИЕ", "action": "Создание новой записи"}
            elif any(action_path in path for action_path in ['/edit/', '/update/', '/change/']):
                return {"type": "✏️ РЕДАКТИРОВАНИЕ", "action": "Редактирование записи"}
            elif any(action_path in path for action_path in ['/delete/', '/remove/']):
                return {"type": "🗑️ УДАЛЕНИЕ", "action": "Удаление записи"}

        # 🔥 СТАТИЧЕСКИЕ ФАЙЛЫ И API КОНСОЛИ (не логируем)
        elif any(static_ext in path for static_ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico']):
            return None
        elif '/api/console-update/' in path:
            return None

        return {"type": "🌐 ПРОСМОТР", "action": "Просмотр страницы"}

    def _get_user_info(self, request):
        """🔍 ПОЛУЧЕНИЕ ИНФОРМАЦИИ О ПОЛЬЗОВАТЕЛЕ"""
        try:
            if hasattr(request, 'user') and request.user.is_authenticated:
                username = request.user.username
                return f"{username}"
            else:
                return "Аноним"
        except:
            return "Неизвестный"

    def _get_client_ip(self, request):
        """🔍 ПОЛУЧЕНИЕ IP-АДРЕСА КЛИЕНТА"""
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')

            return ip if ip else 'unknown'

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения IP: {e}")
            return 'unknown'

    def _analyze_user_agent(self, user_agent_string):
        """🔍 АНАЛИЗ USER-AGENT"""
        ua = user_agent_string.lower()

        # Определяем устройство
        if any(word in ua for word in ['mobile', 'android', 'iphone']):
            device_type = '📱 Мобильный'
        elif any(word in ua for word in ['tablet', 'ipad']):
            device_type = '📟 Планшет'
        else:
            device_type = '💻 ПК'

        # Определяем браузер
        if 'chrome' in ua and 'edg' not in ua:
            browser = 'Chrome'
        elif 'firefox' in ua:
            browser = 'Firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            browser = 'Safari'
        elif 'edg' in ua:
            browser = 'Edge'
        elif 'opera' in ua:
            browser = 'Opera'
        else:
            browser = 'Other'

        # Определяем ОС
        if 'windows' in ua:
            os = 'Windows'
        elif 'mac' in ua:
            os = 'Mac OS'
        elif 'linux' in ua:
            os = 'Linux'
        elif 'android' in ua:
            os = 'Android'
        elif 'ios' in ua or 'iphone' in ua:
            os = 'iOS'
        else:
            os = 'Unknown'

        return {
            'device_type': device_type,
            'browser': browser,
            'os': os
        }

    def _get_status_emoji(self, status_code):
        """🎯 ПОЛУЧЕНИЕ ЭМОДЗИ ДЛЯ СТАТУСА ОТВЕТА"""
        if 200 <= status_code < 300:
            return '✅'
        elif 300 <= status_code < 400:
            return '🔄'
        elif 400 <= status_code < 500:
            return '⚠️'
        elif 500 <= status_code < 600:
            return '❌'
        else:
            return '❓'

    def process_exception(self, request, exception):
        """🔴 ОБРАБОТКА ИСКЛЮЧЕНИЙ"""
        try:
            duration = time.time() - getattr(request, 'start_time', time.time())
            ip_address = self._get_client_ip(request)

            logger.error(
                f"💥 ИСКЛЮЧЕНИЕ: {request.method} {request.path} | "
                f"IP: {ip_address} | "
                f"Time: {duration:.3f}s | "
                f"Error: {str(exception)}"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка логирования исключения: {e}")

        return None


class StaticFilesLoggingMiddleware:
    """📁 ЛОГИРОВАНИЕ ЗАПРОСОВ К СТАТИЧЕСКИМ ФАЙЛАМ"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        """Логируем только статические файлы"""
        if (request.path.startswith('/static/') or
                request.path.startswith('/media/') or
                any(ext in request.path for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico'])):

            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time

                # Логируем только медленные запросы к статике
                if duration > 0.3:
                    logger.warning(
                        f"📁 МЕДЛЕННЫЙ СТАТИЧЕСКИЙ ФАЙЛ: {request.path} | "
                        f"Time: {duration:.3f}s | "
                        f"Size: {len(response.content) if hasattr(response, 'content') else 0} bytes"
                    )

        return response