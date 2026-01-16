from apps.website.models import NotificationCache
from apps.notifications.services import ToastNotificationSystem
from django.utils import timezone


class NotificationCacheManager:
    """Менеджер для работы с кэшем уведомлений и toast"""

    @staticmethod
    def notify_new_product(request, product_data):
        """
        Уведомление о новом товаре с проверкой на дубликаты

        Args:
            request: HttpRequest объект
            product_data: словарь с данными товара
                {
                    'product_id': str,
                    'normalized_url': str,
                    'product_name': str,
                    'price': str,
                    'location': str,
                    'category': str
                }
        """
        # Проверяем на дубликат
        is_duplicate = NotificationCache.is_duplicate(
            product_data['product_id'],
            product_data['normalized_url']
        )

        if not is_duplicate:
            # Добавляем в кэш
            NotificationCache.add_to_cache(
                product_data['product_id'],
                product_data['normalized_url'],
                product_data['product_name']
            )

            # Формируем сообщение для toast
            message = f"""
            <div class="toast-product-notification">
                <div class="toast-product-name">{product_data['product_name']}</div>
                <div class="toast-product-price">💰 {product_data.get('price', 'Цена не указана')}</div>
                <div class="toast-product-location">📍 {product_data.get('location', 'Местоположение не указано')}</div>
                <div class="toast-product-category">🏷️ {product_data.get('category', 'Категория не указана')}</div>
                <button class="toast-view-button" onclick="window.open('{product_data['normalized_url']}', '_blank')">
                    Посмотреть товар
                </button>
            </div>
            """

            # Показываем toast уведомление
            ToastNotificationSystem.success(
                request,
                message,
                'Новый товар найден!',
                position='toast-top-right',
                timeOut=8000,
                progressBar=True,
                closeButton=True,
                template='materialize'  # Используем новый стиль
            )

            return True

        return False

    @staticmethod
    def notify_parser_status(request, status_data):
        """
        Уведомление о статусе парсера

        Args:
            request: HttpRequest объект
            status_data: словарь со статусом парсера
                {
                    'status': 'success'|'error'|'warning',
                    'message': str,
                    'items_found': int,
                    'duration': str
                }
        """
        status = status_data.get('status', 'info')
        message = status_data.get('message', '')
        items_found = status_data.get('items_found', 0)

        if status == 'success' and items_found > 0:
            title = f'Парсер завершен: найдено {items_found} товаров'
            message = f"{message}\nВремя работы: {status_data.get('duration', 'N/A')}"

            ToastNotificationSystem.success(
                request,
                message,
                title,
                position='toast-top-right',
                timeOut=6000,
                progressBar=True,
                template='materialize'
            )

        elif status == 'warning':
            ToastNotificationSystem.warning(
                request,
                message,
                'Предупреждение парсера',
                position='toast-top-right',
                timeOut=5000,
                template='materialize'
            )

        elif status == 'error':
            ToastNotificationSystem.error(
                request,
                message,
                'Ошибка парсера',
                position='toast-top-center',
                timeOut=7000,
                template='materialize'
            )

    @staticmethod
    def notify_user_action(request, action_type, details):
        """
        Уведомление о действиях пользователя

        Args:
            request: HttpRequest объект
            action_type: тип действия ('profile_update', 'search_saved', 'favorite_added', etc.)
            details: дополнительные детали
        """
        action_messages = {
            'profile_update': {
                'type': 'success',
                'title': 'Профиль обновлен',
                'message': 'Ваши данные были успешно сохранены.'
            },
            'search_saved': {
                'type': 'info',
                'title': 'Поиск сохранен',
                'message': 'Поисковый запрос добавлен в избранное.'
            },
            'favorite_added': {
                'type': 'success',
                'title': 'Добавлено в избранное',
                'message': 'Товар добавлен в список избранных.'
            },
            'favorite_removed': {
                'type': 'info',
                'title': 'Удалено из избранного',
                'message': 'Товар удален из списка избранных.'
            },
            'subscription_updated': {
                'type': 'success',
                'title': 'Подписка обновлена',
                'message': 'Настройки подписки успешно изменены.'
            },
            'balance_added': {
                'type': 'success',
                'title': 'Баланс пополнен',
                'message': f'Ваш баланс успешно пополнен на {details.get("amount", 0)} руб.'
            }
        }

        config = action_messages.get(action_type, {
            'type': 'info',
            'title': 'Уведомление',
            'message': 'Действие выполнено.'
        })

        ToastNotificationSystem._add_toast(
            request,
            config['type'],
            config['message'],
            config['title'],
            position='toast-top-right',
            timeOut=4000,
            progressBar=True,
            closeButton=True,
            template='materialize'
        )


# Глобальный экземпляр для удобства
notification_cache = NotificationCacheManager()