import logging
from telegram import Bot
from telegram.error import TelegramError
from shared.utils.config import get_bot_token

# ✅ Создаем логгер для менеджера групп
logger = logging.getLogger('bot.group_manager')


class GroupManager:
    def __init__(self):
        self.bot_token = get_bot_token()
        self.bot = Bot(token=self.bot_token) if self.bot_token else None
        self.max_members = 4  # Максимальное количество участников (включая бота)

    async def can_send_to_group(self, group_id):
        """Проверяет, можно ли отправлять в группу"""
        try:
            if not self.bot:
                logger.error("❌ Бот не инициализирован для проверки группы")
                return False

            chat = await self.bot.get_chat(group_id)
            members_count = await chat.get_member_count()

            logger.info(f"👥 Группа {group_id}: {members_count} участников")

            if members_count > self.max_members:
                await self.send_warning(group_id, members_count)
                return False
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки группы {group_id}: {e}")
            return True  # Разрешаем отправку при ошибке проверки

    async def send_warning(self, group_id, current_count):
        """Отправляет предупреждение в группу"""
        try:
            warning_text = f"""
⚠️ **ОГРАНИЧЕНИЕ БОТА**

👥 **Текущее количество участников:** {current_count}
🚫 **Максимально допустимо:** {self.max_members}

📋 **Для продолжения работы:**
• Уменьшите количество участников до {self.max_members}
• Или свяжитесь с поддержкой для увеличения лимита

🔒 *Бот временно приостановил отправку уведомлений*
            """
            await self.bot.send_message(
                chat_id=group_id,
                text=warning_text,
                parse_mode='Markdown'
            )
            logger.info(f"⚠️ Отправлено предупреждение в группу {group_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка отправки предупреждения: {e}")

    async def safe_send_message(self, group_id, message_text, image_data=None, button_text="", button_url=""):
        """Безопасная отправка с проверкой группы"""
        try:
            # Проверяем можно ли отправлять в группу
            if not await self.can_send_to_group(group_id):
                logger.warning(f"🚫 Отправка в группу {group_id} заблокирована (превышен лимит участников)")
                return False

            # Ленивый импорт чтобы избежать циклической зависимости
            import sys
            if 'bot.bot' not in sys.modules:
                from apps.bot.bot import bot_instance
            else:
                # Альтернативный способ если модуль уже загружен
                bot_instance = sys.modules['bot.bot'].bot_instance

            if bot_instance:
                return await bot_instance.send_notification_with_image(
                    message_text, image_data, button_text, button_url
                )
            else:
                logger.error("❌ Экземпляр бота не доступен")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка безопасной отправки: {e}")
            return False

    async def get_group_info(self, group_id):
        """Получает информацию о группе"""
        try:
            if not self.bot:
                logger.error("❌ Бот не инициализирован для получения информации о группе")
                return None

            chat = await self.bot.get_chat(group_id)
            members_count = await chat.get_member_count()

            group_info = {
                'id': chat.id,
                'title': chat.title,
                'type': chat.type,
                'members_count': members_count,
                'is_over_limit': members_count > self.max_members
            }

            logger.info(f"📊 Информация о группе {group_id}: {members_count} участников, лимит: {self.max_members}")
            return group_info

        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о группе: {e}")
            return None

    async def check_all_groups(self, group_ids):
        """Проверяет статус нескольких групп"""
        try:
            logger.info(f"🔍 Проверяем статус {len(group_ids)} групп...")

            results = {}
            for group_id in group_ids:
                group_info = await self.get_group_info(group_id)
                if group_info:
                    results[group_id] = group_info
                    status = "✅ В норме" if not group_info['is_over_limit'] else "🚫 Превышен лимит"
                    logger.info(f"   👥 Группа {group_id}: {group_info['members_count']} участников - {status}")
                else:
                    results[group_id] = None
                    logger.warning(f"   ⚠️ Не удалось получить информацию о группе {group_id}")

            logger.info(
                f"✅ Проверка групп завершена: {len([r for r in results.values() if r and not r['is_over_limit']])}/{len(results)} групп в норме")
            return results

        except Exception as e:
            logger.error(f"❌ Ошибка проверки групп: {e}")
            return {}

    async def send_test_to_group(self, group_id, test_message="Тестовое сообщение"):
        """Отправляет тестовое сообщение в группу"""
        try:
            logger.info(f"🧪 Отправляем тестовое сообщение в группу {group_id}")

            if not await self.can_send_to_group(group_id):
                logger.warning(f"🚫 Тестовая отправка в группу {group_id} заблокирована")
                return False

            message = f"""
🧪 **ТЕСТОВОЕ СООБЩЕНИЕ**

{test_message}

✅ Группа проверена
👥 Лимит участников: {self.max_members}
🕒 Время отправки

#тест #группа #проверка
            """

            await self.bot.send_message(
                chat_id=group_id,
                text=message,
                parse_mode='Markdown'
            )

            logger.info(f"✅ Тестовое сообщение отправлено в группу {group_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки тестового сообщения: {e}")
            return False


# Глобальный экземпляр менеджера групп
group_manager = GroupManager()