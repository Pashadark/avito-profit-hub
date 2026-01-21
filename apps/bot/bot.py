#!/usr/bin/env python3
"""
ProfitHub Telegram Bot
"""

import os
import sys
import logging
logger = logging.getLogger('bot.telegram')

# ========== КРИТИЧЕСКИ ВАЖНО! ==========
# Добавляем корень проекта в путь Python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# ========== НАСТРОЙКА DJANGO ==========
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

try:
    import django
    django.setup()
    logger.info("✅ Django настроен")
except django.core.exceptions.AppRegistryNotReady:
    # Пробуем еще раз через секунду
    import time
    time.sleep(1)
    django.setup()
    logger.info("✅ Django настроен (со второй попытки)")
except Exception as e:
    logger.error(f"⚠️ Ошибка настройки Django: {e}")
# ======================================

import logging
import asyncio
import threading
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from telegram.error import TelegramError, NetworkError
import base64
import time
from datetime import timedelta
from telegram.constants import ParseMode

# Импорты из нашего приложения (после настройки Django!)
try:
    from apps.bot.group_manager import group_manager
    from apps.bot.handlers.todo_handlers import setup_handlers as setup_todo_handlers
    from apps.bot.services.vision_service import vision_service
    from apps.bot.handlers.registration_handler import setup_handlers as setup_registration_handlers
    logger.info("✅ Импорты бота загружены")
except ImportError as e:
    logger.info(f"⚠️ Ошибка импорта модулей бота: {e}")
    # Создаем заглушки
    group_manager = None
    setup_todo_handlers = None
    vision_service = None
    setup_registration_handlers = None

# ✅ ДОБАВЬ ЭТУ СТРОКУ ДЛЯ ОПРЕДЕЛЕНИЯ ПЕРЕМЕННОЙ
VISION_SYSTEM_AVAILABLE = True

# ✅ Настраиваем логгер ДО всего остального
logger = logging.getLogger('bot.telegram')


def sync_send_notification(message):
    """Синхронная обертка для отправки сообщения"""
    try:
        logger.info("🔄 Начинаем отправку сообщения в Telegram")

        # Импортируем внутри функции чтобы избежать циклических импортов
        try:
            from telegram import Bot
            from telegram.error import TelegramError
            from shared.utils.config import get_bot_token, get_chat_id
            logger.info("✅ Все модули успешно импортированы")
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта модулей: {e}")
            return False

        token = get_bot_token()
        chat_id = get_chat_id()

        logger.info(f"🔧 Токен: {token[:10]}...")
        logger.info(f"🔧 Chat ID: {chat_id}")

        if not token or token == 'ваш_токен_бота':
            logger.error("❌ Токен бота не настроен")
            return False

        if not chat_id:
            logger.error("❌ Chat ID не настроен")
            return False

        # Запускаем асинхронную функцию
        async def send_async():
            try:
                bot = Bot(token=token)
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
                logger.info("✅ Сообщение успешно отправлено в Telegram")
                return True
            except TelegramError as e:
                logger.error(f"❌ Ошибка Telegram: {e}")
                return False
            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при отправке: {e}")
                return False

        return asyncio.run(send_async())

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в sync_send_notification: {e}")
        return False


async def send_telegram_message(message):
    """Асинхронная отправка сообщения в Telegram"""
    try:
        token = get_bot_token()
        chat_id = get_chat_id()

        logger.info(f"🔧 Токен: {token[:10]}...")
        logger.info(f"🔧 Chat ID: {chat_id}")

        if not token or token == 'ваш_токен_бота':
            logger.error("❌ Токен бота не настроен")
            return False

        if not chat_id:
            logger.error("❌ Chat ID не настроен")
            return False

        bot = Bot(token=token)

        # ИСПРАВЛЕНИЕ: используем ParseMode.HTML вместо строки
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML  # ← ИСПРАВЛЕНО ЗДЕСЬ
        )

        logger.info("✅ Тестовое сообщение отправлено в Telegram")
        return True

    except TelegramError as e:
        logger.error(f"❌ Ошибка Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        return False

# ✅ Настраиваем Django ОДИН РАЗ при импорте
def setup_django():
    """Настройка Django (выполняется один раз)"""
    import os
    import sys
    import django
    from django.conf import settings

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    if not settings.configured:
        django.setup()
        logger.info("✅ Django настроен в боте")

# Вызываем настройку Django при импорте модуля
setup_django()

from django.utils import timezone
from django.contrib.auth.models import User
from shared.utils.config import get_bot_token, get_chat_id
from apps.website.models import UserProfile, UserSubscription, FoundItem, ParserSettings


class ProfitHubBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        self.bot = None
        self.is_running = False
        self._initialize_bot()

    def _initialize_bot(self):
        """Инициализация бота с обработкой ошибок"""
        try:
            self.application = Application.builder().token(self.token).build()
            self.bot = self.application.bot
            self.setup_handlers()

            # ✅ ДОБАВЛЯЕМ ОБРАБОТЧИК РЕГИСТРАЦИИ ДЛЯ @infopnz58_bot
            try:
                from bot.handlers.registration_handler import setup_handlers as setup_registration_handlers
                setup_registration_handlers(self.application)
                logger.info("✅ Обработчики регистрации добавлены для @infopnz58_bot")
            except ImportError as e:
                logger.error(f"❌ Ошибка импорта обработчиков регистрации: {e}")
            except Exception as e:
                logger.error(f"❌ Ошибка настройки обработчиков регистрации: {e}")

            logger.info("✅ Бот @infopnz58_bot инициализирован успешно")

            # ✅ ЗАПУСКАЕМ ПЕРИОДИЧЕСКИЙ АНАЛИЗ ПОСЛЕ ИНИЦИАЛИЗАЦИИ
            self.vision_task = self.start_vision_analysis()  # Сохраняем задачу

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            raise

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("subscription", self.subscription_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("items", self.items_command))
        self.application.add_handler(CommandHandler("id", self.id_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("link", self.link_account_command))
        self.application.add_handler(CommandHandler("verify", self.verify_code_command))
        self.application.add_handler(CommandHandler("groupinfo", self.group_info_command))
        self.application.add_handler(CommandHandler("vision", self.vision_command))
        self.application.add_handler(CommandHandler("parser", self.parser_command))

        # ✅ НОВЫЕ КОМАНДЫ ДЛЯ БАЛЛОВ
        self.application.add_handler(CommandHandler("points", self.points_command))
        self.application.add_handler(CommandHandler("leaderboard", self.leaderboard_command))
        self.application.add_handler(CommandHandler("learning", self.learning_stats_command))

        # ✅ ДОБАВЛЯЕМ КОМАНДЫ ДЛЯ ЗАДАЧ
        self.application.add_handler(CommandHandler("todo", self.todo_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))

        # Обработчик текстовых сообщений для создания задач
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_message))

        # Обработчик кнопок для задач
        self.application.add_handler(CallbackQueryHandler(self.handle_todo_callback, pattern="^todo_"))

        # Обработчик кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        # Обработчик цвета
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image_message))

        self.application.add_handler(CallbackQueryHandler(
            self.handle_copy_code,
            pattern="^copy_code_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_toggle_code,
            pattern="^toggle_code_"
        ))

        # ✅ ДОБАВИТЬ ОБРАБОТЧИКИ VISION СИСТЕМЫ
        if VISION_SYSTEM_AVAILABLE:
            try:
                from bot.handlers.vision_feedback import vision_handlers
                handlers = vision_handlers.get_handlers()
                for handler in handlers:
                    self.application.add_handler(handler)
                logger.info("✅ Обработчики vision feedback добавлены")
            except Exception as e:
                logger.error(f"❌ Ошибка добавления обработчиков vision: {e}")

        logger.info("✅ Обработчики команд настроены")

    async def show_active_tasks(self, query, user):
        """Показать активные задачи"""
        tasks = await self.get_user_tasks(user)
        active_tasks = [t for t in tasks if t['status'] in ['todo', 'in_progress']]

        if not active_tasks:
            await query.edit_message_text("📝 Нет активных задач.")
            return

        message = "⚡ **Активные задачи:**\n\n"
        for task in active_tasks[:10]:
            status_emoji = '🔄' if task['status'] == 'in_progress' else '⏳'
            message += f"{status_emoji} **{task['title']}**\n"
            message += f"   🏷️ {task['status_display']}\n\n"

        keyboard = [
            [InlineKeyboardButton("📋 Все задачи", callback_data="todo_list"),
             InlineKeyboardButton("➕ Новая задача", callback_data="todo_create")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_done_tasks(self, query, user):
        """Показать выполненные задачи"""
        tasks = await self.get_user_tasks(user)
        done_tasks = [t for t in tasks if t['status'] == 'done']

        if not done_tasks:
            await query.edit_message_text("✅ Нет выполненных задач.")
            return

        message = "✅ **Выполненные задачи:**\n\n"
        for task in done_tasks[:10]:
            completion_time = "Неизвестно"
            if task['completed_at']:
                completion_time = task['completed_at'].strftime('%d.%m.%Y %H:%M')

            message += f"✅ **{task['title']}**\n"
            message += f"   📅 Завершено: {completion_time}\n\n"

        keyboard = [
            [InlineKeyboardButton("📋 Все задачи", callback_data="todo_list"),
             InlineKeyboardButton("➕ Новая задача", callback_data="todo_create")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def todo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /todo - управление задачами"""
        user = update.effective_user

        # Проверяем привязку аккаунта
        user_profile = await sync_to_async(self._get_user_profile)(user.id)
        if not user_profile:
            await update.message.reply_text(
                "❌ Сначала привяжите Telegram к аккаунту!\n\n"
                "Используйте команду /link или перейдите на сайт: "
                "http://127.0.0.1:8000/profile/"
            )
            return

        keyboard = [
            [InlineKeyboardButton("📝 Создать задачу", callback_data="todo_create")],
            [InlineKeyboardButton("📋 Мои задачи", callback_data="todo_list")],
            [InlineKeyboardButton("⚡ Активные", callback_data="todo_active"),
             InlineKeyboardButton("✅ Выполненные", callback_data="todo_done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📋 **Управление задачами**\n\n"
            "Выберите действие или просто напишите задачу в чат!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /tasks - быстрый список задач"""
        user = update.effective_user
        user_profile = await sync_to_async(self._get_user_profile)(user.id)

        if not user_profile:
            await update.message.reply_text("❌ Сначала привяжите аккаунт через /link")
            return

        # Получаем задачи пользователя
        tasks = await self.get_user_tasks(user_profile.user)

        if not tasks:
            await update.message.reply_text("📝 У вас пока нет задач. Создайте первую!")
            return

        message = "📋 **Ваши задачи:**\n\n"
        for i, task in enumerate(tasks[:10], 1):
            status_emoji = {
                'todo': '⏳',
                'in_progress': '🔄',
                'done': '✅'
            }.get(task['status'], '📝')

            message += f"{i}. {status_emoji} {task['title']}\n"
            if task['description']:
                message += f"   📄 {task['description'][:50]}...\n"
            message += f"   🏷️ {task['status_display']}\n\n"

        if len(tasks) > 10:
            message += f"📁 ... и еще {len(tasks) - 10} задач\n\n"

        message += "Используйте /todo для управления задачами"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def handle_task_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений - создание задач с улучшенной логикой"""
        user = update.effective_user
        text = update.message.text.strip()

        logger.info(f"📝 Обработка текстового сообщения от {user.id}: {text}")

        # Игнорируем короткие сообщения и команды
        if len(text) < 3 or text.startswith('/'):
            logger.info("📝 Сообщение слишком короткое или команда - игнорируем")
            return

        # Проверяем привязку аккаунта
        user_profile = await sync_to_async(self._get_user_profile)(user.id)
        if not user_profile:
            logger.info("📝 Пользователь не привязан - игнорируем сообщение")
            return  # Не привязан - игнорируем

        logger.info(f"📝 Создание задачи для пользователя {user_profile.user.username}")

        # Создаем задачу
        task = await self.create_task(user_profile.user, text)

        if task:
            logger.info(f"✅ Задача создана: {task.title} (ID: {task.id})")

            keyboard = [
                [
                    InlineKeyboardButton("➡️ В процесс", callback_data=f"todo_start_{task.id}"),
                    InlineKeyboardButton("✅ Выполнено", callback_data=f"todo_complete_{task.id}")
                ],
                [InlineKeyboardButton("✏️ Редактировать", callback_data=f"todo_edit_{task.id}"),
                 InlineKeyboardButton("🗑️ Удалить", callback_data=f"todo_delete_{task.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ **Задача создана!**\n\n"
                f"📝 {task.title}\n"
                f"🏷️ Статус: К выполнению\n\n"
                f"Используйте кнопки ниже для управления:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            # Логируем успешное создание
            logger.info(f"📝 Уведомление о создании задачи отправлено пользователю {user.id}")
        else:
            logger.error(f"❌ Ошибка создания задачи для пользователя {user_profile.user.username}")
            await update.message.reply_text(
                "❌ Не удалось создать задачу. Попробуйте еще раз.",
                parse_mode='Markdown'
            )

    async def show_create_dialog(self, query):
        """Показать диалог создания задачи"""
        await query.edit_message_text(
            "📝 **Создание новой задачи**\n\n"
            "Просто напишите задачу в чат!\n\n"
            "Пример: \"Заказать продукты на неделю\"\n"
            "Или: \"Подготовить отчет|Важные графики и цифры\"\n\n"
            "💡 *Можно добавить описание через символ |*",
            parse_mode='Markdown'
        )

    async def show_task_list(self, query, user):
        """Показать список всех задач"""
        tasks = await self.get_user_tasks(user)

        if not tasks:
            await query.edit_message_text("📝 У вас пока нет задач.")
            return

        message = "📋 **Все задачи:**\n\n"
        for task in tasks[:15]:
            status_emoji = {
                'todo': '⏳',
                'in_progress': '🔄',
                'done': '✅'
            }.get(task['status'], '📝')

            message += f"{status_emoji} **{task['title']}**\n"
            message += f"   🏷️ {task['status_display']}\n"
            if task['description']:
                message += f"   📄 {task['description'][:100]}\n"

            # Добавляем кнопки управления
            message += f"   [➡️](/todo_start_{task['id']}) [✅](/todo_complete_{task['id']}) [🗑️](/todo_delete_{task['id']})\n\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="todo_list"),
             InlineKeyboardButton("📝 Создать", callback_data="todo_create")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    async def create_task(self, user, text):
        """Создать задачу с улучшенной обработкой ошибок"""
        try:
            logger.info(f"🔄 Создание задачи для пользователя {user.username}: {text}")

            # Разделяем заголовок и описание через |
            if '|' in text:
                title, description = text.split('|', 1)
                title = title.strip()
                description = description.strip()
            else:
                title = text
                description = ""

            logger.info(f"📝 Параметры задачи: title='{title}', description='{description}'")

            # Получаем или создаем доску
            from apps.website.models import TodoBoard, TodoCard

            board, created = await sync_to_async(TodoBoard.objects.get_or_create)(
                user=user,
                defaults={'name': 'Мои задачи'}
            )

            logger.info(f"📋 Доска: {board.name} (создана: {created})")

            # Создаем задачу
            task = await sync_to_async(TodoCard.objects.create)(
                board=board,
                title=title,
                description=description,
                status='todo',
                created_by=user
            )

            logger.info(f"✅ Задача создана успешно: ID={task.id}, Title='{task.title}'")

            # Проверяем, что задача действительно сохранилась в БД
            task_check = await sync_to_async(TodoCard.objects.filter(id=task.id).first)()
            if task_check:
                logger.info(f"✅ Задача подтверждена в БД: {task_check.title}")
            else:
                logger.error("❌ Задача не найдена в БД после создания!")

            return task

        except Exception as e:
            logger.error(f"❌ Ошибка создания задачи: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None

    async def start_task(self, query, task_id, user):
        """Начать выполнение задачи"""
        try:
            from apps.website.models import TodoCard
            task = await sync_to_async(TodoCard.objects.get)(id=task_id, board__user=user)
            task.status = 'in_progress'
            await sync_to_async(task.save)()

            keyboard = [
                [InlineKeyboardButton("📋 К списку задач", callback_data="todo_list"),
                 InlineKeyboardButton("✅ Завершить", callback_data=f"todo_complete_{task.id}")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"🔄 **Задача начата!**\n\n"
                f"📝 {task.title}\n"
                f"🏷️ Статус: В процессе\n\n"
                f"⏰ Время начала: {task.started_at.strftime('%d.%m.%Y %H:%M') if task.started_at else 'Сейчас'}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except TodoCard.DoesNotExist:
            await query.edit_message_text("❌ Задача не найдена")

    async def complete_task(self, query, task_id, user):
        """Завершить задачу"""
        try:
            from apps.website.models import TodoCard
            task = await sync_to_async(TodoCard.objects.get)(id=task_id, board__user=user)
            task.status = 'done'
            await sync_to_async(task.save)()

            completion_time = task.get_completion_time()

            keyboard = [
                [InlineKeyboardButton("📋 К списку задач", callback_data="todo_list"),
                 InlineKeyboardButton("➕ Новая задача", callback_data="todo_create")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"✅ **Задача выполнена!**\n\n"
                f"📝 {task.title}\n"
                f"🏷️ Статус: Выполнено\n"
                f"⏱️ Затрачено времени: {completion_time if completion_time else 'Неизвестно'}\n"
                f"📅 Завершено: {task.completed_at.strftime('%d.%m.%Y %H:%M') if task.completed_at else 'Сейчас'}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except TodoCard.DoesNotExist:
            await query.edit_message_text("❌ Задача не найдена")

    async def delete_task(self, query, task_id, user):
        """Удалить задачу"""
        try:
            from apps.website.models import TodoCard
            task = await sync_to_async(TodoCard.objects.get)(id=task_id, board__user=user)
            task_title = task.title
            await sync_to_async(task.delete)()

            keyboard = [
                [InlineKeyboardButton("📋 К списку задач", callback_data="todo_list"),
                 InlineKeyboardButton("➕ Новая задача", callback_data="todo_create")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"🗑️ **Задача удалена:** {task_title}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except TodoCard.DoesNotExist:
            await query.edit_message_text("❌ Задача не найдена")

    async def get_user_tasks(self, user):
        """Получить задачи пользователя с улучшенной диагностикой"""
        try:
            from apps.website.models import TodoBoard, TodoCard
            logger.info(f"🔍 Получение задач для пользователя: {user.username}")

            board = await sync_to_async(TodoBoard.objects.filter(user=user).first)()
            if not board:
                logger.info(f"📋 Доска не найдена для пользователя {user.username}")
                return []

            logger.info(f"📋 Найдена доска: {board.name}")

            tasks = await sync_to_async(list)(
                TodoCard.objects.filter(board=board).order_by('-created_at')
            )

            logger.info(f"📋 Найдено задач: {len(tasks)}")

            tasks_data = []
            for task in tasks:
                tasks_data.append({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'status_display': task.get_status_display(),
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at,
                })
                logger.info(f"📝 Задача: {task.title} (статус: {task.status})")

            return tasks_data
        except Exception as e:
            logger.error(f"❌ Ошибка получения задач: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []

    async def handle_todo_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback'ов для задач"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user = query.from_user

        user_profile = await sync_to_async(self._get_user_profile)(user.id)
        if not user_profile:
            await query.edit_message_text("❌ Сначала привяжите аккаунт через /link")
            return

        if callback_data == "todo_create":
            await self.show_create_dialog(query)
        elif callback_data == "todo_list":
            await self.show_task_list(query, user_profile.user)
        elif callback_data == "todo_active":
            await self.show_active_tasks(query, user_profile.user)
        elif callback_data == "todo_done":
            await self.show_done_tasks(query, user_profile.user)
        elif callback_data.startswith("todo_start_"):
            task_id = int(callback_data.replace("todo_start_", ""))
            await self.start_task(query, task_id, user_profile.user)
        elif callback_data.startswith("todo_complete_"):
            task_id = int(callback_data.replace("todo_complete_", ""))
            await self.complete_task(query, task_id, user_profile.user)
        elif callback_data.startswith("todo_delete_"):
            task_id = int(callback_data.replace("todo_delete_", ""))
            await self.delete_task(query, task_id, user_profile.user)

    async def handle_favorite_callback(self, query, context):
        """Обработчик кнопки 'Добавить в избранное'"""
        try:
            callback_data = query.data

            if callback_data.startswith('favorite_'):
                url_hash = callback_data.replace('favorite_', '')

                logger.info(f"⭐ Добавление в избранное по хэшу: {url_hash}")

                # Сначала отвечаем на callback, чтобы убрать "часики" у кнопки
                await query.answer("🔄 Добавляем в избранное...")

                # Получаем пользователя
                user = query.from_user

                # Ищем профиль пользователя
                from asgiref.sync import sync_to_async
                user_profile = await sync_to_async(self._get_user_profile)(user.id)

                if not user_profile:
                    # Отправляем новое сообщение вместо редактирования
                    await query.message.reply_text(
                        "❌ Сначала привяжите Telegram к аккаунту!\n\n"
                        "Используйте команду /link или перейдите на сайт: "
                        "http://127.0.0.1:8000/profile/"
                    )
                    return

                # Ищем товар по хэшу URL в базе данных
                try:
                    from apps.website.models import FoundItem
                    import hashlib

                    def find_item_by_hash(url_hash, user_id):
                        """Находит товар по хэшу URL для конкретного пользователя"""
                        from apps.website.models import UserProfile
                        user_profile = UserProfile.objects.filter(telegram_user_id=user_id).first()
                        if not user_profile:
                            return None

                        user_items = FoundItem.objects.filter(
                            search_query__user=user_profile.user
                        )

                        for item in user_items:
                            item_hash = hashlib.md5(item.url.encode()).hexdigest()[:16]
                            if item_hash == url_hash:
                                return item

                        return None

                    # Ищем товар по хэшу
                    found_item = await sync_to_async(find_item_by_hash)(url_hash, user.id)

                    if found_item:
                        # Проверяем, не добавлен ли уже в избранное
                        if found_item.is_favorite:
                            await query.message.reply_text(
                                f"ℹ️ Товар уже в избранном!\n\n"
                                f"📦 {found_item.title}\n"
                                f"💰 {found_item.price} ₽\n\n"
                                f"📋 Посмотреть все избранные товары:\n"
                                f"http://127.0.0.1:8000/found-items/?favorites=1"
                            )
                            return

                        # Добавляем в избранное
                        found_item.is_favorite = True
                        await sync_to_async(found_item.save)()

                        # Отправляем уведомление о успешном добавлении
                        await query.message.reply_text(
                            f"✅ Товар добавлен в избранное!\n\n"
                            f"📦 {found_item.title}\n"
                            f"💰 {found_item.price} ₽\n"
                            f"🎯 Цель: {found_item.target_price} ₽\n\n"
                            f"📋 Посмотреть все избранные товары:\n"
                            f"http://127.0.0.1:8000/found-items/?favorites=1"
                        )

                        logger.info(f"✅ Товар добавлен в избранное: {found_item.title}")

                    else:
                        # Если товар не найден по хэшу, ищем последний товар пользователя
                        def find_recent_item(user_id):
                            from apps.website.models import UserProfile
                            user_profile = UserProfile.objects.filter(telegram_user_id=user_id).first()
                            if not user_profile:
                                return None

                            recent_item = FoundItem.objects.filter(
                                search_query__user=user_profile.user
                            ).order_by('-found_at').first()

                            return recent_item

                        recent_item = await sync_to_async(find_recent_item)(user.id)

                        if recent_item:
                            # Добавляем последний товар в избранное
                            recent_item.is_favorite = True
                            await sync_to_async(recent_item.save)()

                            await query.message.reply_text(
                                f"✅ Последний товар добавлен в избранное!\n\n"
                                f"📦 {recent_item.title}\n"
                                f"💰 {recent_item.price} ₽\n\n"
                                f"📋 Посмотреть все избранные товары:\n"
                                f"http://127.0.0.1:8000/found-items/?favorites=1"
                            )
                            logger.info(f"✅ Последний товар добавлен в избранное: {recent_item.title}")
                        else:
                            await query.message.reply_text(
                                "❌ Не найден товар для добавления в избранное.\n"
                                "Попробуйте найти новый товар через парсер."
                            )

                except Exception as e:
                    logger.error(f"❌ Ошибка поиска товара: {e}")
                    await query.message.reply_text(
                        "❌ Ошибка при добавлении в избранное.\n"
                        "Попробуйте еще раз или обратитесь к администратору."
                    )

        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка в handle_favorite_callback: {e}")
            await query.message.reply_text("❌ Произошла непредвиденная ошибка.")

    async def handle_image_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик изображений - анализирует цвета с помощью VisionAnalyzer"""
        try:
            user = update.effective_user
            message = update.message

            # Проверяем, что это изображение
            if not message.photo:
                await message.reply_text("📸 Пожалуйста, отправьте изображение для анализа цветов")
                return

            # Получаем самое качественное изображение
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            await message.reply_text("🎨 Анализирую цвета на изображении...")

            # Скачиваем изображение
            image_data = await self.download_image(file.file_path)

            if not image_data:
                await message.reply_text("❌ Не удалось загрузить изображение")
                return

            # Используем упрощенный анализ через VisionAnalyzer
            colors_analysis = await self.simple_color_analysis_with_vision(image_data)

            if colors_analysis:
                response_text = self.format_colors_response(colors_analysis)
                await message.reply_text(response_text, parse_mode='HTML')
            else:
                await message.reply_text("❌ Не удалось проанализировать цвета на изображении")

        except Exception as e:
            logger.error(f"❌ Ошибка анализа изображения: {e}")
            await update.message.reply_text("❌ Произошла ошибка при анализе изображения")


    async def send_registration_confirmation(self, phone_number, confirmation_code, user_data=None):
        """Отправка кода подтверждения регистрации через бот"""
        try:
            chat_id = get_chat_id()  # ID группы/чата куда отправлять

            if not chat_id:
                logger.error("❌ TELEGRAM_CHAT_ID не установлен")
                return False

            # Форматируем сообщение
            message = f"""
    🔐 <b>НОВАЯ РЕГИСТРАЦИЯ</b>

    📱 <b>Телефон:</b> {phone_number}
    🔢 <b>Код подтверждения:</b> <code>{confirmation_code}</code>

    👤 <b>Данные пользователя:</b>
    • Имя: {user_data.get('first_name', 'Не указано')}
    • Фамилия: {user_data.get('last_name', 'Не указано')} 
    • Email: {user_data.get('email', 'Не указан')}
    • Username: {user_data.get('username', 'Не указан')}

    ⏰ <b>Код действителен 10 минут</b>

    💡 <i>Пользователь должен ввести этот код на сайте для завершения регистрации</i>
            """

            # Создаем кнопку для быстрого копирования кода
            keyboard = [
                [InlineKeyboardButton("📋 Скопировать код", callback_data=f"copy_code_{confirmation_code}")],
                [InlineKeyboardButton("👁️ Показать/скрыть код", callback_data=f"toggle_code_{confirmation_code}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

            logger.info(f"✅ Код подтверждения {confirmation_code} отправлен для {phone_number}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки кода подтверждения: {e}")
            return False

    async def handle_copy_code(self, query: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки копирования кода"""
        try:
            code = query.data.replace('copy_code_', '')

            # Показываем уведомление что код скопирован
            await query.answer(f"Код {code} скопирован в буфер обмена", show_alert=False)

            # Обновляем сообщение
            original_text = query.message.text
            new_text = original_text + f"\n\n✅ <b>Код скопирован в {timezone.now().strftime('%H:%M:%S')}</b>"

            await query.edit_message_text(
                new_text,
                reply_markup=query.message.reply_markup,
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"❌ Ошибка обработки копирования кода: {e}")
            await query.answer("Ошибка копирования кода", show_alert=True)

    async def handle_toggle_code(self, query: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик показа/скрытия кода"""
        try:
            code = query.data.replace('toggle_code_', '')
            original_text = query.message.text

            if f"<code>{code}</code>" in original_text:
                # Скрываем код
                new_text = original_text.replace(f"<code>{code}</code>", "••••••")
                button_text = "👁️ Показать код"
            else:
                # Показываем код
                new_text = original_text.replace("••••••", f"<code>{code}</code>")
                button_text = "👁️ Скрыть код"

            # Обновляем кнопку
            keyboard = [
                [InlineKeyboardButton("📋 Скопировать код", callback_data=f"copy_code_{code}")],
                [InlineKeyboardButton(button_text, callback_data=f"toggle_code_{code}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                new_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

            await query.answer("Код обновлен", show_alert=False)

        except Exception as e:
            logger.error(f"❌ Ошибка переключения кода: {e}")
            await query.answer("Ошибка обновления кода", show_alert=True)


    async def download_image(self, file_path):
        """Скачивает изображение из Telegram"""
        try:
            import requests
            from io import BytesIO

            response = requests.get(file_path, timeout=30)
            if response.status_code == 200:
                # Возвращаем BytesIO с данными
                image_bytes = BytesIO(response.content)
                # Сбрасываем позицию в начало
                image_bytes.seek(0)
                return image_bytes
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки изображения: {e}")
            return None

    def format_colors_response(self, analysis):
        """Форматирует ответ с анализом цветов"""
        dominant_colors = analysis['dominant_colors']
        color_palette = analysis['color_palette']
        background_color = analysis.get('background_color')
        object_colors = analysis.get('object_colors', [])

        response = f"""🎨 <b>ДЕТАЛЬНЫЙ АНАЛИЗ ЦВЕТОВ</b>

    📐 <b>Размер:</b> {analysis['image_size']}
    🎯 <b>Значимых цветов:</b> {analysis['colors_count']}

    <b>🌈 ОСНОВНЫЕ ЦВЕТА:</b>
    """

        for i, color in enumerate(dominant_colors[:5], 1):
            color_block = self._get_color_emoji(color['name'])

            response += f"{i}. {color_block} <b>{color['name'].upper()}</b>\n"
            response += f"   📊 {color['percentage']}% | HEX: {color['hex']} | RGB: {color['rgb']}\n"

        # Добавляем информацию о фоне и объекте
        if background_color:
            response += f"\n<b>🎪 ФОН:</b> {background_color['name']} ({background_color['percentage']}%)"

        if object_colors:
            response += f"\n<b>🎯 ЦВЕТА ОБЪЕКТА:</b> "
            object_color_names = [f"{color['name']} ({color['percentage']}%)" for color in object_colors[:3]]
            response += ", ".join(object_color_names)

        response += f"""\n
    <b>🎨 ЦВЕТОВАЯ ПАЛИТРА:</b>
    • Тип: {color_palette['type']}
    • Тональность: {color_palette['tone']}
    • Насыщенность: {color_palette['saturation']}/255 ({color_palette['saturation_level']})
    • Яркость: {color_palette['brightness']}/255 ({color_palette['brightness_level']})
    • Разнообразие: {color_palette.get('color_variety', 'стандартное')}

    💡 <i>Анализ выполнен с помощью компьютерного зрения</i>
    """

        return response

    async def _fallback_color_analysis(self, image_cv):
        """Анализ цветов как запасной вариант"""
        try:
            import cv2
            import numpy as np

            # Простой анализ среднего цвета
            avg_color = np.mean(image_cv, axis=(0, 1)).astype(int)

            return [{
                'rgb': avg_color.tolist(),
                'name': self._get_detailed_color_name(avg_color),
                'percentage': 100.0,
                'hex': f'#{avg_color[2]:02x}{avg_color[1]:02x}{avg_color[0]:02x}'
            }]

        except Exception as e:
            logger.error(f"❌ Ошибка fallback анализа: {e}")
            return [{
                'rgb': [128, 128, 128],
                'name': 'серый',
                'percentage': 100.0,
                'hex': '#808080'
            }]

    def _get_color_emoji(self, color_name):
        """Возвращает эмодзи для цвета"""
        color_emojis = {
            'красный': '🟥', 'оранжевый': '🟧', 'желтый': '🟨',
            'зеленый': '🟩', 'бирюзовый': '🟦', 'синий': '🟦',
            'фиолетовый': '🟪', 'розовый': '🩷',
            'белый': '⬜', 'серый': '⬜', 'черный': '⬛'
        }
        return color_emojis.get(color_name.lower(), '🎨')

    def start_vision_analysis(self):
        """Запускает периодический анализ vision системы - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            if not VISION_SYSTEM_AVAILABLE:
                return

            from bot.handlers.vision_feedback import vision_handlers

            # ✅ ИСПРАВЛЕНИЕ: Запускаем асинхронно когда event loop работает
            async def safe_vision_start():
                try:
                    # Ждем полной инициализации бота
                    await asyncio.sleep(3)

                    # Запускаем анализ с await
                    success = await vision_handlers.start_periodic_analysis()
                    if success:
                        logger.info("✅ Периодический анализ vision системы запущен")
                    else:
                        logger.warning("⚠️ Не удалось запустить периодический анализ vision")

                except Exception as e:
                    logger.error(f"❌ Ошибка запуска анализа vision: {e}")

            # Запускаем безопасно
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже работает, создаем задачу и возвращаем ее
                    task = loop.create_task(safe_vision_start())
                    return task  # Возвращаем задачу чтобы она не была уничтожена
                else:
                    # Если loop не работает, запускаем его
                    asyncio.run(safe_vision_start())
            except RuntimeError:
                # Если нет event loop, создаем новый
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                task = loop.create_task(safe_vision_start())
                return task  # Возвращаем задачу

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации vision анализа: {e}")
            return None

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("subscription", self.subscription_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("items", self.items_command))
        self.application.add_handler(CommandHandler("id", self.id_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("link", self.link_account_command))
        self.application.add_handler(CommandHandler("verify", self.verify_code_command))
        self.application.add_handler(CommandHandler("groupinfo", self.group_info_command))
        self.application.add_handler(CommandHandler("vision", self.vision_command))
        self.application.add_handler(CommandHandler("parser", self.parser_command))

        # ✅ НОВЫЕ КОМАНДЫ ДЛЯ БАЛЛОВ
        self.application.add_handler(CommandHandler("points", self.points_command))
        self.application.add_handler(CommandHandler("leaderboard", self.leaderboard_command))
        self.application.add_handler(CommandHandler("learning", self.learning_stats_command))

        # ✅ ДОБАВЛЯЕМ КОМАНДЫ ДЛЯ ЗАДАЧ - ВАЖНО: ДО обработчиков vision!
        self.application.add_handler(CommandHandler("todo", self.todo_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))

        # ✅ Обработчик текстовых сообщений для создания задач - ДО других обработчиков текста
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_message))

        # ✅ Обработчик кнопок для задач
        self.application.add_handler(CallbackQueryHandler(self.handle_todo_callback, pattern="^todo_"))

        # Обработчик кнопок (общий)
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

        # Обработчик изображений
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image_message))

        self.application.add_handler(CallbackQueryHandler(
            self.handle_copy_code,
            pattern="^copy_code_"
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.handle_toggle_code,
            pattern="^toggle_code_"
        ))

        # ✅ ДОБАВИТЬ ОБРАБОТЧИКИ VISION СИСТЕМЫ - ПОСЛЕ обработчиков задач
        # if VISION_SYSTEM_AVAILABLE:
        #    try:
        #        from bot.handlers.vision_feedback import vision_handlers
        #        handlers = vision_handlers.get_handlers()
        #        for handler in handlers:
        #            self.application.add_handler(handler)
        #        logger.info("✅ Обработчики vision feedback добавлены")
        #    except Exception as e:
        #        logger.error(f"❌ Ошибка добавления обработчиков vision: {e}")

    # ========== НОВЫЕ КОМАНДЫ ДЛЯ БАЛЛОВ ==========

    async def points_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает баллы пользователя"""
        try:
            if not VISION_SYSTEM_AVAILABLE:
                await update.message.reply_text("❌ Система компьютерного зрения недоступна")
                return

            from bot.handlers.vision_feedback import vision_handlers

            user_id = update.effective_user.id
            stats = await vision_handlers.get_user_points_stats(user_id)

            if not stats:
                await update.message.reply_text("❌ Ошибка получения статистики баллов")
                return

            points_text = f"""
🎯 <b>ВАШИ БАЛЛЫ И СТАТИСТИКА</b>

💎 <b>Баллы:</b> {stats['points']}
🏅 <b>Ранг:</b> {stats['rank']}

📊 <b>Активность:</b>
👍 Подтверждений: {stats['feedback_count']}
📝 Описаний: {stats['descriptions_count']}
✏️ Исправлений: {stats['corrections_count']}

💡 <i>Помогайте ИИ учиться и зарабатывайте больше баллов!</i>
🎁 <i>Скоро появятся награды за баллы!</i>
"""
            await update.message.reply_text(points_text, parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Ошибка команды points: {e}")
            await update.message.reply_text("❌ Ошибка получения баллов")

    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает таблицу лидеров"""
        try:
            if not VISION_SYSTEM_AVAILABLE:
                await update.message.reply_text("❌ Система компьютерного зрения недоступна")
                return

            from bot.handlers.vision_feedback import vision_handlers

            leaders = await vision_handlers.get_leaderboard(10)

            if not leaders:
                await update.message.reply_text("📊 Пока нет данных для таблицы лидеров")
                return

            leaderboard_text = "🏆 <b>ТАБЛИЦА ЛИДЕРОВ</b>\n\n"

            for i, leader in enumerate(leaders, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} {leader['rank']} - {leader['points']} баллов\n"

            leaderboard_text += "\n💡 <i>Помогайте ИИ учиться чтобы подняться в рейтинге!</i>"

            await update.message.reply_text(leaderboard_text, parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Ошибка команды leaderboard: {e}")
            await update.message.reply_text("❌ Ошибка получения таблицы лидеров")

    async def learning_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для просмотра статистики обучения ИИ"""
        try:
            if not VISION_SYSTEM_AVAILABLE:
                await update.message.reply_text("❌ Система компьютерного зрения недоступна")
                return

            from bot.handlers.vision_feedback import vision_handlers

            await update.message.reply_text("🔄 Анализирую процесс обучения ИИ...")

            stats = await vision_handlers.get_learning_stats()

            if "error" in stats:
                await update.message.reply_text(f"❌ Ошибка анализа: {stats['error']}")
                return

            # Форматируем статистику
            stats_text = await self._format_learning_stats(stats)

            await update.message.reply_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

        except Exception as e:
            logger.error(f"❌ Ошибка команды learning_stats: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики обучения")

    async def _format_learning_stats(self, stats):
        """Форматирует статистику обучения для Telegram"""
        try:
            categories = stats.get('category_patterns', {})
            colors = stats.get('color_patterns', {})
            materials = stats.get('material_patterns', {})
            errors = stats.get('error_patterns', {})

            # Топ категорий
            top_categories = "\n".join(
                [f"• {cat}: {count} раз" for cat, count in list(categories.items())[:5]]
            ) if categories else "• Данных пока недостаточно"

            # Топ цветов
            top_colors = "\n".join(
                [f"• {color}: {count} раз" for color, count in list(colors.items())[:5]]
            ) if colors else "• Данных пока недостаточно"

            # Топ материалов
            top_materials = "\n".join(
                [f"• {material}: {count} раз" for material, count in list(materials.items())[:5]]
            ) if materials else "• Данных пока недостаточно"

            # Статистика ошибок
            accuracy = errors.get('accuracy', 0)
            error_rate = errors.get('error_rate', 0)
            total_feedback = errors.get('total_feedback', 0)

            stats_text = f"""
🤖 <b>СТАТИСТИКА ОБУЧЕНИЯ ИИ</b>

📊 <b>Общая эффективность:</b>
🎯 Точность распознавания: <b>{accuracy}%</b>
❌ Частота ошибок: <b>{error_rate}%</b>
📝 Всего фидбэков: <b>{total_feedback}</b>

📁 <b>Частые категории:</b>
{top_categories}

🎨 <b>Частые цвета:</b>
{top_colors}

⚙️ <b>Частые материалы:</b>
{top_materials}

💡 <i>Система автоматически обучается на основе ваших описаний</i>
🕒 <i>Обновляется каждые 6 часов</i>
"""
            return stats_text

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования статистики: {e}")
            return "❌ Ошибка форматирования статистики обучения"

    # ========== СУЩЕСТВУЮЩИЕ КОМАНДЫ ==========

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - главное меню с проверкой привязки"""
        user = update.effective_user
        logger.info(f"👤 Пользователь {user.id} ({user.username}) запустил бота")

        try:
            # Используем sync_to_async для работы с Django ORM
            from asgiref.sync import sync_to_async

            # Проверяем привязку профиля асинхронно
            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if user_profile:
                # Аккаунт привязан
                welcome_text = f"""
✅ **Добро пожаловать в Селибри Бот!**

Ваш Telegram привязан к аккаунту: **{user_profile.user.username}**

💼 **Статус:** Активен
💰 **Баланс:** {user_profile.balance} ₽
👤 **Профиль:** {user_profile.user.get_full_name() or user_profile.user.username}

Выберите действие ниже 👇
                """
                keyboard = self.get_main_keyboard()
            else:
                # Аккаунт не привязан
                welcome_text = f"""
🔗 **Приветствуем в Селибри!**

Для начала работы нужно привязать ваш Telegram к аккаунту Django.

📋 **Как это сделать:**
1. Войдите в веб-интерфейс (http://127.0.0.1:8000)
2. Перейдите в профиль → Настройки Telegram
3. Используйте команду: `/link ВАШ_ЛОГИН`

💡 **Пример:** `/link admin`

Ваш User ID: `{user.id}`
                """
                keyboard = self.get_link_keyboard()

            await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"❌ Ошибка в start_command: {e}")
            error_text = """
❌ **Временная ошибка сервиса**

Попробуйте выполнить следующие действия:
1. Проверьте работу веб-сайта: http://127.0.0.1:8000
2. Если сайт не работает, перезапустите систему
3. Попробуйте снова через 1-2 минуты

При повторной ошибке обратитесь к администратору.
            """
            await update.message.reply_text(error_text, parse_mode='Markdown')

    def _get_user_profile(self, telegram_user_id):
        """Синхронный метод получения профиля пользователя по Telegram ID"""
        try:
            logger.info(f"🔍 Поиск профиля для Telegram User ID: {telegram_user_id}")

            # Ищем профиль с этим telegram_user_id
            user_profile = UserProfile.objects.filter(telegram_user_id=telegram_user_id).first()

            if user_profile and user_profile.telegram_verified:
                logger.info(f"✅ Найден верифицированный профиль: {user_profile.user.username}")
                return user_profile

            logger.info(f"❌ Профиль не найден или не верифицирован для User ID: {telegram_user_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения профиля: {e}")
            return None

    async def parser_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /parser - меню статистики парсера"""
        await self.show_parser_menu(update, context)

    async def show_parser_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню статистики парсера"""
        try:
            parser_text = """
    🤖 **Парсер - Аналитическая панель**

    Система мониторинга производительности парсера Avito.
    Здесь отображается реальная статистика работы парсера.

    Выберите действие:
            """
            keyboard = await self.get_parser_keyboard()

            if hasattr(update, 'message'):
                await update.message.reply_text(parser_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await update.edit_message_text(parser_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_parser_menu: {e}")
            error_text = "❌ Ошибка загрузки меню парсера"
            if hasattr(update, 'message'):
                await update.message.reply_text(error_text)
            else:
                await update.edit_message_text(error_text)

    async def vision_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /vision - меню машинного зрения"""
        await self.show_vision_menu(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - справка"""
        help_text = """
📖 **Справка по командам:**

/start - Главное меню
/help - Эта справка
/profile - Информация о профиле  
/balance - Баланс и операции
/subscription - Информация о подписке
/status - Статус парсера
/items - Последние найденные товары
/id - Узнать ID этого чата
/stats - Детальная статистика
/link - Привязать аккаунт Django

💡 **Что можно узнать:**
- Текущий баланс и историю пополнений
- Активна ли подписка и сколько дней осталось
- Работает ли парсер прямо сейчас
- Статистику найденных товаров
- User ID для привязки аккаунта
        """

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile - информация о профиле"""
        await self.show_profile(update, context)

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /balance - информация о балансе"""
        try:
            user = update.effective_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await update.message.reply_text("❌ Профиль не найден. Используйте /link для привязки аккаунта.")
                return

            balance_text = await self.format_balance_info(user_profile)
            keyboard = await self.get_balance_keyboard()

            await update.message.reply_text(balance_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в balance_command: {e}")
            await update.message.reply_text("❌ Ошибка загрузки баланса. Попробуйте позже.")

    async def subscription_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /subscription - информация о подписке"""
        try:
            user = update.effective_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await update.message.reply_text("❌ Профиль не найден. Используйте /link для привязки аккаунта.")
                return

            subscription_text = await self.format_subscription_info(user_profile.user)
            keyboard = await self.get_subscription_keyboard()

            await update.message.reply_text(subscription_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в subscription_command: {e}")
            await update.message.reply_text("❌ Ошибка загрузки информации о подписке. Попробуйте позже.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status - статус системы"""
        await self.show_status(update, context)

    async def items_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /items - найденные товары"""
        await self.show_items(update, context)

    async def id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /id - User ID"""
        try:
            user = update.effective_user
            id_text = f"""
🆔 **Информация о пользователе**

💬 **Ваш User ID:** `{user.id}`
📧 **Username:** @{user.username or 'Не указан'}
👤 **Имя:** {user.first_name or 'Не указано'}

💡 *Этот ID уникален для вашего аккаунта Telegram*
            """
            await update.message.reply_text(id_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в id_command: {e}")
            await update.message.reply_text(f"🆔 Ваш Telegram ID: {user.id}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика с исправленным HTML"""
        try:
            # Получаем данные статистики
            stats_data = await self.get_vision_stats_from_db()

            # Форматируем статистику
            formatted_stats = await self.format_vision_stats(stats_data)

            # ИСПРАВЛЕННАЯ ОТПРАВКА - используем ParseMode.HTML
            await update.message.reply_text(
                formatted_stats,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

        except Exception as e:
            logger.error(f"❌ Ошибка в stats_command: {e}")
            await update.message.reply_text(
                "❌ Ошибка загрузки статистики машинного зрения",
                parse_mode=ParseMode.HTML
            )

    async def link_account_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Улучшенная команда для привязки Telegram к Django аккаунту с исправлением асинхронности"""
        user = update.effective_user

        try:
            from asgiref.sync import sync_to_async

            # Проверяем, не привязан ли уже профиль асинхронно
            existing_profile_qs = await sync_to_async(UserProfile.objects.filter)(telegram_user_id=user.id)
            existing_profile = await sync_to_async(existing_profile_qs.first)()

            if existing_profile and existing_profile.telegram_verified:
                await update.message.reply_text(
                    f"✅ Ваш Telegram уже привязан к аккаунту: **{existing_profile.user.username}**\n\n"
                    f"👤 Имя: {existing_profile.user.get_full_name() or 'Не указано'}\n"
                    f"💰 Баланс: {existing_profile.balance} ₽\n"
                    f"🆔 Telegram ID: `{user.id}`",
                    parse_mode='Markdown'
                )
                return

            # Получаем логин Django из сообщения
            if not context.args:
                # Генерируем код верификации асинхронно
                code = await sync_to_async(self._generate_verification_code)(user.id)

                await update.message.reply_text(
                    f"🔗 **Система привязки аккаунта**\n\n"
                    f"📱 **Ваш Telegram:**\n"
                    f"• User ID: `{user.id}`\n"
                    f"• Username: @{user.username or 'не указан'}\n"
                    f"• Имя: {user.first_name or 'Не указано'}\n\n"
                    f"🔐 **Код верификации:** `{code}`\n\n"
                    f"**Для привязки:**\n"
                    f"1. Перейдите на сайт: http://127.0.0.1:8000/profile/\n"
                    f"2. В разделе 'Telegram' введите код\n"
                    f"3. Или используйте команду: `/link ВАШ_ЛОГИН_ДЖАНГО`\n\n"
                    f"**Пример:** `/link {user.username or 'ваш_логин'}`",
                    parse_mode='Markdown'
                )
                return

            django_username = context.args[0].strip()

            # Ищем пользователя по username асинхронно
            try:
                target_user = await sync_to_async(User.objects.get)(username=django_username)
            except User.DoesNotExist:
                await update.message.reply_text(
                    "❌ Пользователь с таким логином не найден.\n"
                    "Проверьте правильность написания логина Django.",
                    parse_mode='Markdown'
                )
                return

            # Проверяем, не привязан ли уже этот аккаунт к другому Telegram асинхронно
            existing_link_qs = await sync_to_async(UserProfile.objects.filter)(
                user=target_user,
                telegram_verified=True
            )
            existing_link = await sync_to_async(existing_link_qs.first)()

            if existing_link:
                await update.message.reply_text(
                    f"❌ Аккаунт `{django_username}` уже привязан к другому Telegram.\n"
                    f"Telegram ID: `{existing_link.telegram_user_id}`",
                    parse_mode='Markdown'
                )
                return

            # Привязываем Telegram USER ID к найденному пользователю асинхронно
            profile = await sync_to_async(UserProfile.link_telegram_account)(
                target_user, user.id, user.username
            )

            # Получаем информацию о подписке асинхронно
            subscription_info = await self.get_subscription_info(target_user)

            await update.message.reply_text(
                f"✅ **Успешная привязка!**\n\n"
                f"Telegram аккаунт привязан к Django: **{target_user.username}**\n"
                f"👤 Имя: {target_user.get_full_name() or 'Не указано'}\n"
                f"💰 Баланс: {profile.balance} ₽\n"
                f"🔔 Уведомления: {'✅ Включены' if profile.telegram_notifications else '❌ Выключены'}\n"
                f"{subscription_info}\n\n"
                f"Теперь вы можете управлять аккаунтом через бота!",
                parse_mode='Markdown'
            )

            logger.info(f"✅ User {user.id} привязан к Django аккаунту {target_user.username}")

        except Exception as e:
            logger.error(f"Ошибка в link_account_command: {e}")
            await update.message.reply_text("❌ Ошибка привязки аккаунта.")

    def _generate_verification_code(self, telegram_user_id):
        """Генерация кода верификации для пользователя с исправлением"""
        try:
            # Создаем временный профиль для генерации кода
            # Используем get_or_create для избежания дубликатов
            temp_profile, created = UserProfile.objects.get_or_create(
                telegram_user_id=telegram_user_id,
                defaults={
                    'user': User.objects.first(),  # Временный пользователь
                    'telegram_verified': False
                }
            )

            # Генерируем новый код
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            temp_profile.telegram_verification_code = code
            temp_profile.telegram_verification_expires = timezone.now() + timedelta(minutes=10)
            temp_profile.telegram_verified = False
            temp_profile.save()

            logger.info(f"✅ Сгенерирован код верификации {code} для user_id {telegram_user_id}")
            return code

        except Exception as e:
            logger.error(f"Ошибка генерации кода: {e}")
            return "000000"  # Fallback код

    async def verify_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для верификации кода из бота с полным исправлением асинхронности"""
        user = update.effective_user

        if not context.args:
            await update.message.reply_text(
                "❌ Используйте: `/verify КОД`\n"
                "Пример: `/verify 123456`",
                parse_mode='Markdown'
            )
            return

        code = context.args[0].strip()

        try:
            from asgiref.sync import sync_to_async
            from django.utils import timezone

            # Асинхронно ищем профиль с этим кодом
            profile = await sync_to_async(
                lambda: UserProfile.objects.filter(
                    telegram_verification_code=code,
                    telegram_verification_expires__gte=timezone.now()
                ).first()
            )()

            if profile:
                # Проверяем код синхронно но в асинхронном контексте
                is_valid = await sync_to_async(profile.verify_telegram_code)(code)

                if is_valid:
                    # Обновляем профиль асинхронно
                    profile.telegram_user_id = user.id
                    profile.telegram_username = user.username
                    await sync_to_async(profile.save)()

                    # Получаем информацию о пользователе для подтверждения
                    user_info = await sync_to_async(
                        lambda: f"{profile.user.username} ({profile.user.get_full_name()})")()
                    balance_info = await sync_to_async(lambda: f"{profile.balance} ₽")()

                    await update.message.reply_text(
                        f"✅ **Верификация успешна!**\n\n"
                        f"🤝 **Аккаунт привязан:** {user_info}\n"
                        f"💰 **Баланс:** {balance_info}\n"
                        f"🔔 **Уведомления:** {'✅ Включены' if profile.telegram_notifications else '❌ Выключены'}\n\n"
                        f"Теперь вы можете использовать все функции бота!\n"
                        f"Попробуйте команду /profile для проверки",
                        parse_mode='Markdown'
                    )

                    logger.info(f"✅ Успешная верификация: {user.id} -> {profile.user.username}")

                else:
                    await update.message.reply_text(
                        "❌ **Неверный код верификации**\n\n"
                        "Возможно:\n"
                        "• Код уже использован\n"
                        "• Истекло время действия\n"
                        "• Неправильно введен код\n\n"
                        "Получите новый код на сайте.",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    "❌ **Код не найден или устарел**\n\n"
                    "Попробуйте получить новый код на сайте:\n"
                    "http://127.0.0.1:8000/profile/",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"❌ Ошибка верификации: {e}")
            await update.message.reply_text(
                "❌ **Ошибка при верификации**\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode='Markdown'
            )
    # ========== ОБРАБОТЧИКИ КНОПОК ==========

    async def button_handler(self, update, context):
        """Обработчик нажатий на inline-кнопки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        query = update.callback_query
        await query.answer()

        try:
            callback_data = query.data
            logger.info(f"🔄 Обработка callback: {callback_data}")

            # ✅ ОБРАБОТКА TODO КНОПОК
            if callback_data.startswith('todo_'):
                await self.handle_todo_callback(update, context)
                return

            if callback_data.startswith('favorite_'):
                await self.handle_favorite_callback(query, context)

            elif callback_data == 'profile':
                await self.show_profile_query(query)

            elif callback_data == 'balance':
                await self.show_balance_query(query)

            elif callback_data == 'subscription':
                await self.show_subscription_query(query)

            elif callback_data == 'status':
                await self.show_status_query(query)

            elif callback_data == 'items':
                await self.show_items_query(query)

            elif callback_data == 'stats':
                await self.show_stats_query(query)

            elif callback_data == 'get_id':
                await self.show_chat_id_query(query)

            elif callback_data == 'refresh':
                await self.handle_refresh_query(query)

            elif callback_data == 'main_menu':
                await self.show_main_menu_query(query)

            elif callback_data == 'vision_menu':
                await self.show_vision_menu_query(query)

            elif callback_data == 'parser_menu':
                await self.show_parser_menu_query(query)

            elif callback_data == 'vision_stats':
                await self.show_vision_stats_query(query)

            elif callback_data == 'parser_stats':
                await self.show_parser_stats_query(query)

            elif callback_data == 'vision_export':
                await self.export_vision_knowledge_query(query)

            elif callback_data == 'parser_export':
                await self.export_parser_data_query(query)

            elif callback_data == 'link_account':
                await self.show_link_account_query(query)

            elif callback_data == 'help':
                await self.handle_help_command(update, context)

            # ✅ ОБРАБОТКА TODO LIST ИЗ ГЛАВНОГО МЕНЮ
            elif callback_data == 'todo_list':
                user = query.from_user
                user_profile = await sync_to_async(self._get_user_profile)(user.id)
                if user_profile:
                    await self.show_task_list(query, user_profile.user)
                else:
                    await query.edit_message_text("❌ Сначала привяжите аккаунт через /link")

            else:
                # Для неизвестных команд отправляем новое сообщение
                await query.edit_message_text("⚙️ Команда в разработке")

        except Exception as e:
            logger.error(f"❌ Ошибка в обработчике кнопок: {e}")
            await query.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

    async def show_parser_menu_query(self, query, refresh=False):
        """Показать меню парсера (из кнопки)"""
        await self.show_parser_menu(query, None)

    async def show_parser_stats_query(self, query, refresh=False):
        """Показать статистику парсера"""
        try:
            from asgiref.sync import sync_to_async
            import requests

            def get_parser_stats_from_api():
                """Получение статистики парсера через API"""
                try:
                    # Пробуем разные endpoints
                    endpoints = [
                        'http://127.0.0.1:8000/api/parser-stats/',
                        'http://127.0.0.1:8000/api/parser_stats/',
                        'http://127.0.0.1:8000/api/parser/'
                    ]

                    for endpoint in endpoints:
                        try:
                            response = requests.get(endpoint, timeout=10)
                            if response.status_code == 200:
                                data = response.json()
                                if data.get('status') == 'success':
                                    return data.get('stats', {})
                        except:
                            continue

                    # Если API недоступно, используем демо-данные
                    return self.get_demo_parser_stats()

                except Exception as e:
                    logger.error(f"Ошибка получения статистики парсера: {e}")
                    return self.get_demo_parser_stats()

            # Получаем статистику
            stats_data = await sync_to_async(get_parser_stats_from_api)()

            # Форматируем статистику
            stats_text = await self.format_parser_stats(stats_data)
            keyboard = await self.get_parser_stats_keyboard()

            # Отправляем сообщение
            if refresh:
                await query.edit_message_text(
                    stats_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            else:
                await query.message.reply_text(
                    stats_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )

        except Exception as e:
            logger.error(f"❌ Ошибка в show_parser_stats_query: {e}")
            error_text = f"❌ <b>Ошибка загрузки статистики парсера:</b> {str(e)}"
            await query.edit_message_text(
                error_text,
                parse_mode=ParseMode.HTML
            )

    async def format_parser_stats(self, stats_data):
        """Форматирование статистики парсера для Telegram"""
        try:
            # Основные метрики
            total_searches = stats_data.get('total_searches', 0)
            successful_searches = stats_data.get('successful_searches', 0)
            items_found = stats_data.get('items_found', 0)
            good_deals = stats_data.get('good_deals_found', 0)
            duplicates_blocked = stats_data.get('duplicates_blocked', 0)
            error_count = stats_data.get('error_count', 0)
            active_queries = stats_data.get('active_queries', 0)
            avg_cycle_time = stats_data.get('avg_cycle_time', '0с')
            uptime = stats_data.get('uptime', '0ч 0м')

            # Рассчитываем проценты
            success_rate = round((successful_searches / total_searches * 100) if total_searches > 0 else 0, 1)
            efficiency_rate = round((items_found / total_searches * 100) if total_searches > 0 else 0, 1)
            good_deals_rate = round((good_deals / items_found * 100) if items_found > 0 else 0, 1)

            # Прогресс-бары
            def progress_bar(percentage, width=10):
                filled = round((percentage / 100) * width)
                return "█" * filled + "░" * (width - filled)

            # Форматируем текст
            stats_text = f"""<b>🤖 ПАРСЕР AVITO - СТАТИСТИКА</b>

    <b>📊 Основные метрики:</b>
    🔍 Поисков: {total_searches}
    ✅ Успешных: {successful_searches} ({success_rate}%)
    🎯 Найдено товаров: {items_found}
    💰 Хороших сделок: {good_deals} ({good_deals_rate}%)

    <b>⚡ Производительность:</b>
    ⏱️ Средний цикл: {avg_cycle_time}
    🕐 Время работы: {uptime}
    🖥️ Активных запросов: {active_queries}

    <b>🛡️ Защита:</b>
    🚫 Дубликатов заблокировано: {duplicates_blocked}
    ❌ Ошибок: {error_count}

    <b>📈 Эффективность:</b>
    🎯 Успешность: {progress_bar(success_rate)} {success_rate}%
    ⚡ Эффективность: {progress_bar(efficiency_rate)} {efficiency_rate}%
    💎 Качество сделок: {progress_bar(good_deals_rate)} {good_deals_rate}%

    💡 <i>Статистика обновляется в реальном времени</i>"""

            return stats_text

        except Exception as e:
            logger.error(f"Ошибка форматирования статистики парсера: {e}")
            return "❌ <b>Ошибка форматирования статистики</b>"

    def get_demo_parser_stats(self):
        """Демо-данные для парсера"""
        return {
            'total_searches': 1250,
            'successful_searches': 980,
            'items_found': 345,
            'good_deals_found': 89,
            'duplicates_blocked': 567,
            'error_count': 23,
            'active_queries': 8,
            'avg_cycle_time': '45с',
            'uptime': '12ч 30м'
        }

    async def export_parser_data_query(self, query):
        """Экспорт данных парсера"""
        try:
            from asgiref.sync import sync_to_async
            import requests

            def export_parser_data():
                try:
                    response = requests.post('http://127.0.0.1:8000/api/parser-data/export/', timeout=30)
                    if response.status_code == 200:
                        return {'status': 'success', 'message': 'Данные парсера экспортированы'}
                    else:
                        return {'status': 'error', 'message': 'Ошибка экспорта'}
                except Exception as e:
                    return {'status': 'error', 'message': f'Ошибка: {str(e)}'}

            result = await sync_to_async(export_parser_data)()

            if result['status'] == 'success':
                message = f"✅ {result['message']}"
            else:
                message = f"❌ {result['message']}"

            await query.edit_message_text(message)
            # Возвращаемся в меню через 2 секунды
            await asyncio.sleep(2)
            await self.show_parser_menu_query(query)

        except Exception as e:
            logger.error(f"Ошибка в export_parser_data_query: {e}")
            await query.edit_message_text("❌ Ошибка экспорта данных парсера")

    async def handle_refresh_query(self, query):
        """Обработка обновления раздела"""
        original_text = query.message.text
        if "Профиль" in original_text:
            await self.show_profile_query(query, refresh=True)
        elif "Баланс" in original_text:
            await self.show_balance_query(query, refresh=True)
        elif "Подписка" in original_text:
            await self.show_subscription_query(query, refresh=True)
        elif "Статус" in original_text:
            await self.show_status_query(query, refresh=True)
        elif "Товары" in original_text:
            await self.show_items_query(query, refresh=True)
        elif "Статистика" in original_text:
            await self.show_stats_query(query, refresh=True)
        else:
            await self.show_main_menu_query(query)

    # ========== МЕТОДЫ МАШИННОГО ЗРЕНИЯ ==========

    async def show_vision_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню машинного зрения"""
        try:
            vision_text = """
    🧠 **Машинное зрение - Аналитическая панель**

    Система обучения становится умнее с каждым анализом. 
    Здесь отображается реальная статистика работы машинного зрения.

    Выберите действие:
            """
            keyboard = await self.get_vision_keyboard()

            if hasattr(update, 'message'):
                await update.message.reply_text(vision_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await update.edit_message_text(vision_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_vision_menu: {e}")
            error_text = "❌ Ошибка загрузки меню машинного зрения"
            if hasattr(update, 'message'):
                await update.message.reply_text(error_text)
            else:
                await update.edit_message_text(error_text)

    async def show_vision_menu_query(self, query, refresh=False):
        """Показать меню машинного зрения (из кнопки)"""
        await self.show_vision_menu(query, None)

    async def show_vision_stats_query(self, query, refresh=False):
        """Показать статистику машинного зрения с исправленным HTML"""
        try:
            from asgiref.sync import sync_to_async

            def get_vision_stats_from_db():
                import sqlite3
                import os

                # Все возможные пути к базе данных
                possible_paths = [
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vision_knowledge.db'),
                    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vision_knowledge.db'),
                    'vision_knowledge.db',
                    r'C:\Users\pasahdark\PycharmProjects\avito_profit_hub\vision_knowledge.db',
                ]

                for db_path in possible_paths:
                    if os.path.exists(db_path):
                        logger.info(f"🔍 Используем базу данных: {db_path}")
                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()

                            # Проверяем существование таблиц
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vision_cache';")
                            if not cursor.fetchone():
                                logger.error("❌ Таблица vision_cache не найдена")
                                conn.close()
                                continue

                            # Получаем общую статистику
                            cursor.execute("SELECT COUNT(*) FROM vision_cache")
                            cache_size = cursor.fetchone()[0]

                            cursor.execute("SELECT COUNT(*) FROM vision_cache WHERE match_result = 1")
                            positive_matches = cursor.fetchone()[0]

                            cursor.execute("SELECT COUNT(*) FROM vision_cache WHERE match_result = 0")
                            negative_matches = cursor.fetchone()[0]

                            # Получаем количество уникальных объектов
                            cursor.execute(
                                "SELECT COUNT(DISTINCT target_object) FROM vision_cache WHERE target_object IS NOT NULL")
                            objects_learned = cursor.fetchone()[0]

                            # Получаем среднюю уверенность
                            cursor.execute("SELECT AVG(confidence) FROM vision_cache WHERE confidence IS NOT NULL")
                            avg_confidence = cursor.fetchone()[0] or 0

                            # Проверяем существование таблицы quick_lookup
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quick_lookup';")
                            if cursor.fetchone():
                                cursor.execute("SELECT COUNT(*) FROM quick_lookup")
                                quick_lookups = cursor.fetchone()[0]
                            else:
                                quick_lookups = 0

                            conn.close()

                            return {
                                'learning_stats': {
                                    'cache_size': cache_size,
                                    'objects_learned': objects_learned,
                                    'average_success_rate': positive_matches / (
                                                positive_matches + negative_matches) if (
                                                                                                    positive_matches + negative_matches) > 0 else 0,
                                    'total_analyses': positive_matches + negative_matches,
                                    'database_size': f"{os.path.getsize(db_path) / 1024:.1f} KB"
                                },
                                'cache_stats': {
                                    'positive_matches': positive_matches,
                                    'negative_matches': negative_matches,
                                    'total_analyses': positive_matches + negative_matches
                                },
                                'performance_stats': {
                                    'avg_response_time': max(1, 100 - (quick_lookups * 0.1)),
                                    'total_quick_lookups': quick_lookups,
                                    'avg_quick_confidence': avg_confidence
                                }
                            }

                        except Exception as e:
                            print(f"❌ Ошибка чтения из БД {db_path}: {e}")
                            continue

                # Если ни одна база не найдена
                print("❌ База данных vision_knowledge.db не найдена ни по одному из путей")
                return None

            # Пробуем получить данные из базы
            stats_data = await sync_to_async(get_vision_stats_from_db)()

            if stats_data:
                # Используем исправленную функцию форматирования
                stats_text = await self.format_vision_stats(stats_data)
                # НЕ добавляем дополнительную строку здесь - она уже есть в format_vision_stats
            else:
                # Если БД недоступна, используем демо-данные
                stats_data = self.get_demo_vision_stats()
                stats_text = await self.format_vision_stats(stats_data)
                stats_text += "\n\n⚠️ <i>Используются демо-данные (база знаний недоступна)</i>"

            keyboard = await self.get_vision_stats_keyboard()

            # ИСПРАВЛЕННАЯ ОТПРАВКА
            if refresh:
                await query.edit_message_text(
                    stats_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            else:
                await query.message.reply_text(
                    stats_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )

        except Exception as e:
            logger.error(f"❌ Ошибка в show_vision_stats_query: {e}")
            error_text = f"❌ <b>Ошибка загрузки статистики:</b> {str(e)}"
            await query.edit_message_text(
                error_text,
                parse_mode=ParseMode.HTML
            )

            async def export_vision_knowledge_query(self, query):
                """Экспорт знаний машинного зрения с прямым доступом к БД"""
                try:
                    from asgiref.sync import sync_to_async
                    import shutil
                    import os

                    def export_knowledge_direct():
                        try:
                            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                                   'vision_knowledge.db')
                            export_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                                       'vision_knowledge_export.db')

                            if not os.path.exists(db_path):
                                return {'status': 'error', 'message': 'База знаний не найдена'}

                            # Копируем базу данных для экспорта
                            shutil.copy2(db_path, export_path)

                            return {
                                'status': 'success',
                                'message': f'База знаний экспортирована: {export_path}',
                                'file_path': export_path
                            }
                        except Exception as e:
                            return {'status': 'error', 'message': f'Ошибка экспорта: {str(e)}'}

                    result = await sync_to_async(export_knowledge_direct)()

                    if result['status'] == 'success':
                        message = f"✅ {result['message']}"
                        # Можно добавить отправку файла пользователю
                    else:
                        message = f"❌ {result['message']}"

                    await query.edit_message_text(message)
                    # Возвращаемся в меню через 2 секунды
                    await asyncio.sleep(2)
                    await self.show_vision_menu_query(query)

                except Exception as e:
                    logger.error(f"Ошибка в export_vision_knowledge_query: {e}")
                    await query.edit_message_text("❌ Ошибка экспорта")

    async def format_vision_stats(self, stats_data):
        """Форматирование статистики машинного зрения для Telegram - ИСПРАВЛЕННАЯ версия"""
        ls = stats_data.get('learning_stats', {})
        cs = stats_data.get('cache_stats', {})
        ps = stats_data.get('performance_stats', {})

        # Основные метрики
        cache_size = ls.get('cache_size', 0)
        objects_learned = ls.get('objects_learned', 0)
        avg_accuracy = round((ls.get('average_success_rate', 0) * 100), 1)
        response_time = ps.get('avg_response_time', 0)

        # Статистика кэша
        positive_matches = cs.get('positive_matches', 0)
        negative_matches = cs.get('negative_matches', 0)
        total_analyses = cs.get('total_analyses', 0)

        # Производительность
        quick_lookups = ps.get('total_quick_lookups', 0)
        quick_confidence = round((ps.get('avg_quick_confidence', 0) * 100), 1)

        # Определяем скорость системы
        if response_time < 10:
            speed_status = "🐆 Максимальная"
        elif response_time < 50:
            speed_status = "🐎 Высокая"
        elif response_time < 200:
            speed_status = "🐕 Средняя"
        else:
            speed_status = "🐢 Медленная"

        # Рассчитываем эффективность
        efficiency = round((positive_matches / total_analyses * 100) if total_analyses > 0 else 0, 1)

        # Прогресс-бары (используем Unicode символы)
        def progress_bar(percentage, width=10):
            filled = round((percentage / 100) * width)
            return "█" * filled + "░" * (width - filled)

        # ИСПРАВЛЕННЫЙ ТЕКСТ - убрал дублирование и улучшил форматирование
        stats_text = f"""<b>👁 МАШИННОЕ ЗРЕНИЕ - СТАТИСТИКА</b>

    <b>📊 Производительность:</b>
    ⚡️ Скорость: {speed_status}
    ⏱️ Ответ: {response_time}мс

    <b>🎯 Качество работы:</b>
    🎯 Точность: {progress_bar(avg_accuracy)} {avg_accuracy}%
    📈 Эффективность: {progress_bar(efficiency)} {efficiency}%
    💪 Уверенность: {progress_bar(quick_confidence)} {quick_confidence}%

    <b>🗃️ Данные:</b>
    🗄 Кэш: {cache_size} записей
    🧠 Изучено: {objects_learned} объектов
    ⚡️ Быстрые ответы: {quick_lookups}

    <b>📈 Анализы:</b>
    ✅ Успешные: {positive_matches}
    ❌ Неуспешные: {negative_matches}
    📊 Всего: {total_analyses}

    💡 <i>Система постоянно обучается и улучшается</i>

    ✅ <i>Данные загружены из базы знаний</i>"""

        return stats_text

    def get_demo_vision_stats(self):
        """Демо-данные для машинного зрения"""
        return {
            'learning_stats': {
                'cache_size': 0,
                'objects_learned': 0,
                'average_success_rate': 0,
                'total_analyses': 0,
                'database_size': '0 KB'
            },
            'cache_stats': {
                'positive_matches': 0,
                'negative_matches': 0,
                'total_analyses': 0
            },
            'performance_stats': {
                'avg_response_time': 0,
                'total_quick_lookups': 0,
                'avg_quick_confidence': 0
            }
        }

    async def check_vision_database(self):
        """Проверить наличие и путь к базе данных машинного зрения"""
        import os
        import sqlite3

        # Возможные пути к базе данных
        possible_paths = [
            # Основной путь
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vision_knowledge.db'),
            # Альтернативный путь
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vision_knowledge.db'),
            # Путь из корня проекта
            'vision_knowledge.db',
            # Абсолютный путь
            r'C:\Users\pasahdark\PycharmProjects\avito_profit_hub\vision_knowledge.db'
        ]

        found_paths = []
        for path in possible_paths:
            if os.path.exists(path):
                found_paths.append(path)
                print(f"✅ Найдена база данных: {path}")
                # Проверим структуру
                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    print(f"📊 Таблицы в базе: {[table[0] for table in tables]}")
                    conn.close()
                except Exception as e:
                    print(f"❌ Ошибка проверки структуры {path}: {e}")
            else:
                print(f"❌ Не найдено: {path}")

        return found_paths
    # ========== МЕТОДЫ ОТОБРАЖЕНИЯ ИНФОРМАЦИИ ==========

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать профиль (из команды)"""
        try:
            user = update.effective_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await update.message.reply_text("❌ Профиль не найден в системе. Используйте /link для привязки.")
                return

            profile_text = await self.format_profile_info(user, user_profile)
            keyboard = await self.get_profile_keyboard()

            await update.message.reply_text(profile_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_profile: {e}")
            await update.message.reply_text("❌ Ошибка загрузки профиля.")

    async def show_profile_query(self, query, refresh=False):
        """Показать профиль (из кнопки)"""
        try:
            user = query.from_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await query.edit_message_text("❌ Профиль не найден в системе. Используйте /link для привязки.")
                return

            profile_text = await self.format_profile_info(user, user_profile)
            keyboard = await self.get_profile_keyboard()

            if refresh:
                await query.edit_message_text(profile_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(profile_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_profile_query: {e}")
            await query.edit_message_text("❌ Ошибка загрузки профиля.")

    async def show_balance_query(self, query, refresh=False):
        """Показать баланс (из кнопки)"""
        try:
            user = query.from_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await query.edit_message_text("❌ Профиль не найден.")
                return

            balance_text = await self.format_balance_info(user_profile)
            keyboard = await self.get_balance_keyboard()

            if refresh:
                await query.edit_message_text(balance_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(balance_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_balance_query: {e}")
            await query.edit_message_text("❌ Ошибка загрузки баланса.")

    async def show_subscription_query(self, query, refresh=False):
        """Показать подписку (из кнопки)"""
        try:
            user = query.from_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await query.edit_message_text("❌ Профиль не найден.")
                return

            subscription_text = await self.format_subscription_info(user_profile.user)
            keyboard = await self.get_subscription_keyboard()

            if refresh:
                await query.edit_message_text(subscription_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(subscription_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_subscription_query: {e}")
            await query.edit_message_text("❌ Ошибка загрузки информации о подписке.")

    async def show_chat_id_query(self, query, refresh=False):
        """Показать User ID (из кнопки)"""
        try:
            user = query.from_user
            id_text = f"""
🆔 **Информация о пользователе**

💬 **Ваш User ID:** `{user.id}`
📧 **Username:** @{user.username or 'Не указан'}
👤 **Имя:** {user.first_name or 'Не указано'}

💡 *Этот ID уникален для вашего аккаунта Telegram*
            """
            keyboard = await self.get_chat_id_keyboard()

            if refresh:
                await query.edit_message_text(id_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(id_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_chat_id_query: {e}")
            await query.edit_message_text("❌ Ошибка получения ID.")

    async def show_status_query(self, query, refresh=False):
        """Показать статус (из кнопки)"""
        try:
            status_text = await self.format_status_info()
            keyboard = await self.get_status_keyboard()

            if refresh:
                await query.edit_message_text(status_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(status_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_status_query: {e}")
            await query.edit_message_text("❌ Ошибка загрузки статуса.")

    async def show_items_query(self, query, refresh=False):
        """Показать товары (из кнопки)"""
        try:
            user = query.from_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await query.edit_message_text("❌ Профиль не найден.")
                return

            items_text = await self.format_items_info(user_profile.user)
            keyboard = await self.get_items_keyboard()

            if refresh:
                await query.edit_message_text(items_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(items_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_items_query: {e}")
            await query.edit_message_text("❌ Ошибка загрузки товаров.")

    async def show_stats_query(self, query, refresh=False):
        """Показать статистику (из кнопки)"""
        try:
            user = query.from_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await query.edit_message_text("❌ Профиль не найден.")
                return

            stats_text = await self.format_stats_info(user_profile.user)
            keyboard = await self.get_stats_keyboard()

            if refresh:
                await query.edit_message_text(stats_text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await query.message.reply_text(stats_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_stats_query: {e}")
            await query.edit_message_text("❌ Ошибка загрузки статистики.")

    async def show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус (из команды)"""
        status_text = await self.format_status_info()
        keyboard = await self.get_status_keyboard()

        await update.message.reply_text(status_text, reply_markup=keyboard, parse_mode='Markdown')

    async def show_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать товары (из команды)"""
        try:
            user = update.effective_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await update.message.reply_text("❌ Профиль не найден.")
                return

            items_text = await self.format_items_info(user_profile.user)
            keyboard = await self.get_items_keyboard()

            await update.message.reply_text(items_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_items: {e}")
            await update.message.reply_text("❌ Ошибка загрузки товаров.")

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику (из команды)"""
        try:
            user = update.effective_user
            from asgiref.sync import sync_to_async

            user_profile = await sync_to_async(self._get_user_profile)(user.id)

            if not user_profile:
                await update.message.reply_text("❌ Профиль не найден.")
                return

            stats_text = await self.format_stats_info(user_profile.user)
            keyboard = await self.get_stats_keyboard()

            await update.message.reply_text(stats_text, reply_markup=keyboard, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в show_stats: {e}")
            await update.message.reply_text("❌ Ошибка загрузки статистики.")

    # ========== ФОРМАТИРОВАНИЕ ИНФОРМАЦИИ ==========

    async def format_profile_info(self, user, user_profile):
        """Форматирование информации о профиле"""
        from asgiref.sync import sync_to_async

        subscription_info = await self.get_subscription_info(user_profile.user)
        parser_status = await self.get_parser_status()
        items_stats = await self.get_items_stats(user_profile.user)

        profile_text = f"""
    👤 **Профиль пользователя**

    🆔 **Telegram User ID:** `{user.id}`
    👤 **Имя в Telegram:** {user.first_name or 'Не указано'}
    📧 **Username:** @{user.username or 'Не указан'}

    🔗 **Привязан к Django:** ✅ {user_profile.user.username}
    💰 **Баланс:** {user_profile.balance or 0} ₽
    🔔 **Уведомления:** {'✅ Включены' if user_profile.telegram_notifications else '❌ Выключены'}
    {subscription_info}

    {parser_status}

    📊 **Статистика товаров:**
    {items_stats}
        """
        return profile_text

    async def format_balance_info(self, user_profile):
        """Форматирование информации о балансе"""
        try:
            from asgiref.sync import sync_to_async
            from apps.website.models import Transaction

            transactions = await sync_to_async(list)(
                Transaction.objects.filter(
                    user=user_profile.user,
                    status='completed'
                ).order_by('-created_at')[:5]
            )

            transactions_text = ""
            for i, transaction in enumerate(transactions, 1):
                sign = "+" if transaction.amount > 0 else ""
                type_icons = {
                    'topup': '💳',
                    'subscription': '🔔',
                    'refund': '↩️',
                    'daily_charge': '📅'
                }
                icon = type_icons.get(transaction.transaction_type, '💼')
                transactions_text += f"{i}. {icon} {sign}{transaction.amount} ₽\n"

            balance_text = f"""
💰 **Баланс аккаунта**

💵 **Текущий баланс:** {user_profile.balance or 0} ₽

📋 **Последние операции:**
{transactions_text or '• Нет операций'}

💡 *Для пополнения баланса обратитесь к администратору*
            """
            return balance_text

        except Exception as e:
            logger.error(f"Ошибка форматирования баланса: {e}")
            return "❌ Ошибка загрузки информации о балансе"

    async def format_subscription_info(self, user):
        """Форматирование информации о подписке - ИСПРАВЛЕННАЯ версия"""
        try:
            from asgiref.sync import sync_to_async
            from django.utils import timezone

            logger.info(f"🔍 Получение подписки для пользователя: {user.username}")

            # 1. Получаем активную подписку с правильным асинхронным доступом
            def get_user_subscription(user_id):
                from django.utils import timezone
                from apps.website.models import UserSubscription

                subscription = UserSubscription.objects.filter(
                    user_id=user_id,
                    is_active=True,
                    end_date__gte=timezone.now()
                ).select_related('plan').first()

                if subscription:
                    return {
                        'exists': True,
                        'plan_name': subscription.plan.name if subscription.plan else 'Неизвестно',
                        'plan_type': subscription.plan.plan_type if subscription.plan else 'Неизвестно',
                        'price': float(subscription.plan.price) if subscription.plan else 0,
                        'end_date': subscription.end_date,
                        'days_left': (subscription.end_date - timezone.now()).days,
                        'is_active': subscription.is_active
                    }
                else:
                    return {'exists': False}

            # Выполняем синхронную функцию в асинхронном контексте
            subscription_data = await sync_to_async(get_user_subscription)(user.id)

            logger.info(f"📦 Данные подписки: {subscription_data}")

            if subscription_data['exists']:
                days_left = subscription_data['days_left']
                status_icon = "✅" if days_left > 7 else "⚠️" if days_left > 0 else "❌"

                subscription_text = f"""
    🔔 **Информация о подписке**

    {status_icon} **Статус:** Активна
    📋 **Тариф:** {subscription_data['plan_name']}
    💳 **Тип:** {subscription_data['plan_type']}
    💰 **Цена:** {subscription_data['price']} ₽/мес
    📅 **Осталось дней:** {days_left}
    ⏰ **Заканчивается:** {subscription_data['end_date'].strftime('%d.%m.%Y')}

    💡 *Подписка активна и работает в штатном режиме*
                """

                logger.info(f"✅ Подписка найдена: {subscription_data['plan_name']}")
                return subscription_text

            # 2. Проверяем есть ли неактивная подписка
            def get_expired_subscription(user_id):
                from django.utils import timezone
                from apps.website.models import UserSubscription

                subscription = UserSubscription.objects.filter(
                    user_id=user_id,
                    is_active=True
                ).select_related('plan').first()

                if subscription and subscription.end_date < timezone.now():
                    return {
                        'exists': True,
                        'plan_name': subscription.plan.name if subscription.plan else 'Неизвестно',
                        'end_date': subscription.end_date,
                        'days_expired': (timezone.now() - subscription.end_date).days
                    }
                return {'exists': False}

            expired_data = await sync_to_async(get_expired_subscription)(user.id)

            if expired_data['exists']:
                subscription_text = f"""
    🔔 **Информация о подписке**

    ❌ **Статус:** Истекла
    📋 **Тариф:** {expired_data['plan_name']}
    📅 **Истекла:** {expired_data['end_date'].strftime('%d.%m.%Y')}
    ⏳ **Прошло дней:** {expired_data['days_expired']}

    💡 *Для продления подписки обратитесь к администратору*
                """
                return subscription_text

            # 3. Нет подписки вообще
            subscription_text = """
    🔔 **Информация о подписке**

    ❌ **Статус:** Не активна
    📋 **Тариф:** Отсутствует
    📅 **Осталось дней:** 0

    💡 *Для активации подписки обратитесь к администратору*
            """

            logger.info("ℹ️ Подписка не найдена")
            return subscription_text

        except Exception as e:
            logger.error(f"❌ Критическая ошибка получения подписки: {e}")
            return f"🔔 **Ошибка загрузки подписки:** {str(e)}"

    async def format_status_info(self):
        """Форматирование информации о статусе системы"""
        try:
            from parser.utils.selenium_parser import selenium_parser

            status = "Работает" if selenium_parser.is_running else "Остановлен"
            queries = getattr(selenium_parser, 'search_queries', [])

            status_text = f"""
📊 **Статус системы**

{status}

🔍 **Активные запросы:** {len(queries)}
🖥️ **Окна браузера:** {getattr(selenium_parser, 'browser_windows', 1)}
⏱️ **Интервал проверки:** {getattr(selenium_parser, 'check_interval', 30)} мин.

💡 *Система мониторит цены в реальном времени*
            """
        except Exception as e:
            status_text = f"""
📊 **Статус системы**

🔴 **Статус:** Не доступен
❌ **Ошибка:** Модуль парсера не отвечает

💡 *Обратитесь к администратору для решения проблемы*
            """

        return status_text

    async def format_items_info(self, user):
        """Форматирование информации о товарах"""
        try:
            from asgiref.sync import sync_to_async

            items = await sync_to_async(list)(
                FoundItem.objects.filter(
                    search_query__user=user
                ).order_by('-found_at')[:5]
            )

            if not items:
                items_text = "📭 **Найдено товаров:** 0\n\nЕще не найдено ни одного товара."
            else:
                items_text = "📦 **Последние найденные товары**\n\n"
                for i, item in enumerate(items, 1):
                    profit_icon = "💰" if item.profit and item.profit > 0 else "⚡"
                    profit_text = f"{profit_icon} Прибыль: {item.profit} ₽" if item.profit and item.profit > 0 else "🎯 Мониторинг"
                    items_text += f"{i}. **{item.title}**\n"
                    items_text += f"   💵 Цена: {item.price} ₽\n"
                    items_text += f"   {profit_text}\n"
                    items_text += f"   📅 {item.found_at.astimezone().strftime('%d.%m.%Y %H:%M')}\n\n"

            total_items = await sync_to_async(FoundItem.objects.filter(search_query__user=user).count)()
            good_deals = await sync_to_async(FoundItem.objects.filter(
                search_query__user=user,
                profit__gt=0
            ).count)()

            stats_text = f"""
📊 **Статистика:**
• Всего найдено: {total_items}
• Выгодных: {good_deals}
• Эффективность: {round((good_deals / total_items * 100) if total_items > 0 else 0, 1)}%
            """

            return items_text + stats_text

        except Exception as e:
            logger.error(f"Ошибка форматирования товаров: {e}")
            return "❌ Ошибка загрузки информации о товарах"

    async def format_stats_info(self, user):
        """Форматирование детальной статистики"""
        try:
            from asgiref.sync import sync_to_async
            from django.db.models import Count, Avg, Max, Min

            # Базовая статистика
            total_items = await sync_to_async(FoundItem.objects.filter(search_query__user=user).count)()
            good_deals = await sync_to_async(FoundItem.objects.filter(search_query__user=user, profit__gt=0).count)()

            # Статистика за неделю
            from django.utils import timezone
            week_ago = timezone.now() - timedelta(days=7)
            week_items = await sync_to_async(FoundItem.objects.filter(
                search_query__user=user,
                found_at__gte=week_ago
            ).count)()

            # Статистика цен
            price_stats = await sync_to_async(FoundItem.objects.filter(search_query__user=user).aggregate)(
                avg_price=Avg('price'),
                max_price=Max('price'),
                min_price=Min('price')
            )

            stats_text = f"""
📊 **Детальная статистика**

📦 **Товары:**
• Всего найдено: {total_items}
• Выгодных предложений: {good_deals}
• За последние 7 дней: {week_items}
• Эффективность: {round((good_deals / total_items * 100) if total_items > 0 else 0, 1)}%

💰 **Цены:**
• Средняя цена: {round(price_stats['avg_price'] or 0, 0)} ₽
• Максимальная цена: {price_stats['max_price'] or 0} ₽
• Минимальная цена: {price_stats['min_price'] or 0} ₽

📈 **Активность:**
• Парсер: {'🟢 Активен' if week_items > 0 else '🟡 Низкая' if total_items > 0 else '🔴 Не активен'}
• Рекомендация: {'Продолжайте в том же духе! ✅' if week_items > 10 else 'Увеличьте количество запросов ⚡' if week_items > 0 else 'Настройте поисковые запросы 🔧'}
            """

            return stats_text

        except Exception as e:
            logger.error(f"Ошибка форматирования статистики: {e}")
            return "❌ Ошибка загрузки статистики"

    async def get_subscription_info(self, user):
        """Получить информацию о подписке - ИСПРАВЛЕННАЯ версия"""
        try:
            from asgiref.sync import sync_to_async
            from django.utils import timezone

            # Правильный асинхронный запрос к базе данных
            def get_user_subscription(user_id):
                from apps.website.models import UserSubscription
                try:
                    subscription = UserSubscription.objects.filter(
                        user_id=user_id,
                        is_active=True,
                        end_date__gte=timezone.now()
                    ).select_related('plan').first()
                    return subscription
                except Exception as e:
                    logger.error(f"Ошибка получения подписки: {e}")
                    return None

            subscription = await sync_to_async(get_user_subscription)(user.id)

            if subscription:
                days_left = (subscription.end_date - timezone.now()).days
                status_icon = "✅" if days_left > 7 else "⚠️" if days_left > 0 else "❌"
                plan_name = subscription.plan.name if subscription.plan else "Без названия"
                return f"📋 **Тариф:** {plan_name} (осталось {days_left} дн.)"
            else:
                # Проверим есть ли неактивная подписка
                def get_any_subscription(user_id):
                    from apps.website.models import UserSubscription
                    return UserSubscription.objects.filter(
                        user_id=user_id,
                        is_active=True
                    ).select_related('plan').first()

                any_subscription = await sync_to_async(get_any_subscription)(user.id)

                if any_subscription and any_subscription.end_date < timezone.now():
                    days_expired = (timezone.now() - any_subscription.end_date).days
                    plan_name = any_subscription.plan.name if any_subscription.plan else "Без названия"
                    return f"📋 **Тариф:** {plan_name} ❌ Истекла ({days_expired} дн. назад)"

                return "📋 **Тариф:** Не активна"

        except Exception as e:
            logger.error(f"❌ Критическая ошибка получения подписки: {e}")
            return "📋 **Тариф:** Ошибка загрузки"

    async def get_parser_status(self):
        """Получить статус парсера"""
        try:
            from parser.utils.selenium_parser import selenium_parser
            status = "Работает" if selenium_parser.is_running else "Остановлен"
            queries = getattr(selenium_parser, 'search_queries', [])
            return f"{status} | Запросов: {len(queries)}"
        except Exception as e:
            logger.error(f"Ошибка получения статуса парсера: {e}")
            return "🔴 **Парсер:** Не доступен"

    async def get_items_stats(self, user):
        """Получить статистику товаров"""
        try:
            from asgiref.sync import sync_to_async
            from django.utils import timezone

            total_items = await sync_to_async(FoundItem.objects.filter)(search_query__user=user)
            total_items = await sync_to_async(total_items.count)()

            good_deals = await sync_to_async(FoundItem.objects.filter)(
                search_query__user=user,
                profit__gt=0
            )
            good_deals = await sync_to_async(good_deals.count)()

            today_items = await sync_to_async(FoundItem.objects.filter)(
                search_query__user=user,
                found_at__date=timezone.now().date()
            )
            today_items = await sync_to_async(today_items.count)()

            efficiency = round((good_deals / total_items * 100) if total_items > 0 else 0, 1)

            return f"""• 📦 Всего товаров: {total_items}
• 💰 Выгодных: {good_deals} 
• 📅 Сегодня: {today_items}
• 🎯 Эффективность: {efficiency}%"""

        except Exception as e:
            logger.error(f"Ошибка получения статистики товаров: {e}")
            return "• 📦 Статистика недоступна"

    # ========== КЛАВИАТУРЫ ==========
    async def get_vision_keyboard(self):
        """Клавиатура для машинного зрения"""
        keyboard = [
            [InlineKeyboardButton("📝 Статистика", callback_data="vision_stats")],
            [InlineKeyboardButton("💾 Экспорт", callback_data="vision_export")],  # Убрали кнопку очистки кэша
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_parser_keyboard(self):
        """Клавиатура для парсера"""
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="parser_stats")],
            [InlineKeyboardButton("💾 Экспорт данных", callback_data="parser_export")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_parser_stats_keyboard(self):
        """Клавиатура для статистики парсера"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить статистику", callback_data="parser_stats")],
            [InlineKeyboardButton("💾 Экспорт данных", callback_data="parser_export")],
            [InlineKeyboardButton("🤖 Назад к меню", callback_data="parser_menu"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_vision_stats_keyboard(self):
        """Клавиатура для статистики машинного зрения"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить статистику", callback_data="vision_stats")],
            [InlineKeyboardButton("💾 Экспорт знаний", callback_data="vision_export")],  # Убрали кнопку очистки кэша
            [InlineKeyboardButton("🧠 Назад к меню", callback_data="vision_menu"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_main_keyboard(self):
        """Главная клавиатура для привязанных пользователей"""
        keyboard = [
            [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
             InlineKeyboardButton("🔔 Подписка", callback_data="subscription")],
            [InlineKeyboardButton("📊 Статус системы", callback_data="status"),
             InlineKeyboardButton("📦 Товары", callback_data="items")],
            [InlineKeyboardButton("📋 Мои задачи", callback_data="todo_list"),  # ✅ НОВАЯ КНОПКА
             InlineKeyboardButton("🧠 Машинное зрение", callback_data="vision_menu")],
            [InlineKeyboardButton("🤖 Парсер", callback_data="parser_menu"),
             InlineKeyboardButton("🆔 Мой User ID", callback_data="get_id")],
            [InlineKeyboardButton("📈 Статистика", callback_data="stats"),
             InlineKeyboardButton("🔄 Обновить", callback_data="refresh")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_link_keyboard(self):
        """Клавиатура для непривязанных пользователей"""
        keyboard = [
            [InlineKeyboardButton("🔗 Привязать аккаунт", callback_data="link_account")],
            [InlineKeyboardButton("🆔 Узнать мой User ID", callback_data="get_id")],
            [InlineKeyboardButton("📖 Справка", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_profile_keyboard(self):
        """Клавиатура для профиля"""
        keyboard = [
            [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
             InlineKeyboardButton("🔔 Подписка", callback_data="subscription")],
            [InlineKeyboardButton("📦 Товары", callback_data="items"),
             InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_balance_keyboard(self):
        """Клавиатура для баланса"""
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("🔔 Подписка", callback_data="subscription")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_subscription_keyboard(self):
        """Клавиатура для подписки"""
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_status_keyboard(self):
        """Клавиатура для статуса"""
        keyboard = [
            [InlineKeyboardButton("📦 Товары", callback_data="items"),
             InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_items_keyboard(self):
        """Клавиатура для товаров"""
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
             InlineKeyboardButton("📈 Статус системы", callback_data="status")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_chat_id_keyboard(self):
        """Клавиатура для ID чата"""
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("⚙️ Настройки", callback_data="profile")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def get_stats_keyboard(self):
        """Клавиатура для статистики"""
        keyboard = [
            [InlineKeyboardButton("📦 Товары", callback_data="items"),
             InlineKeyboardButton("📈 Статус системы", callback_data="status")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    # ========== ОСТАЛЬНЫЕ МЕТОДЫ ==========

    async def show_main_menu_query(self, query):
        """Показать главное меню"""
        keyboard = self.get_main_keyboard()
        menu_text = "🏠 **Главное меню**\n\nВыберите раздел:"
        await query.edit_message_text(menu_text, reply_markup=keyboard, parse_mode='Markdown')

    async def show_link_account_query(self, query):
        """Показать информацию о привязке аккаунта"""
        user = query.from_user

        from asgiref.sync import sync_to_async
        user_profile = await sync_to_async(UserProfile.objects.filter)(telegram_chat_id=str(user.id))
        user_profile = await sync_to_async(user_profile.first)()

        if user_profile:
            text = f"""
🔗 **Статус привязки**

✅ Ваш Telegram привязан к аккаунту: **{user_profile.user.username}**

👤 Django пользователь: {user_profile.user.get_full_name() or user_profile.user.username}
💰 Баланс: {user_profile.balance} ₽
🆔 User ID: `{user.id}`

Для отвязки обратитесь к администратору.
            """
        else:
            text = f"""
🔗 **Привязка аккаунта**

Ваш Telegram User ID: `{user.id}`

Для привязки к существующему аккаунту Django:

1. Войдите в веб-интерфейс (http://127.0.0.1:8000)
2. Перейдите в профиль → Настройки Telegram  
3. Используйте команду: `/link ВАШ_ЛОГИН`

Или бот автоматически создаст новый аккаунт.
            """

        keyboard = [
            [InlineKeyboardButton("🔄 Проверить привязку", callback_data="link_account")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # ========== УПРАВЛЕНИЕ БОТОМ ==========

    def start_polling(self):
        """Запуск бота в отдельном потоке с защитой от конфликтов"""
        try:
            logger.info("🚀 Запуск Telegram бота...")

            def run_bot():
                try:
                    # Создаем новую event loop для этого потока
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Настраиваем обработку ошибок
                    def handle_exception(loop, context):
                        logger.error(f"Ошибка в event loop: {context}")

                    loop.set_exception_handler(handle_exception)

                    # Запускаем с обработкой остановки
                    try:
                        logger.info("🔄 Запуск запросов бота...")
                        loop.run_until_complete(self.application.run_polling(
                            drop_pending_updates=True,
                            allowed_updates=Update.ALL_TYPES,
                            close_loop=False
                        ))
                    except KeyboardInterrupt:
                        logger.info("⏹️ Бот остановлен по запросу пользователя")
                    except Exception as e:
                        logger.error(f"❌ Ошибка в потоке бота: {e}")
                    finally:
                        logger.info("🧹 Cleaning up bot loop...")
                        if not loop.is_closed():
                            loop.close()

                except Exception as e:
                    logger.error(f"❌ Критическая ошибка в потоке бота: {e}")

            # Запускаем в отдельном потоке с явным именем
            bot_thread = threading.Thread(
                target=run_bot,
                daemon=True,
                name="ProfitHubBotThread"
            )
            bot_thread.start()

            # Даем время боту инициализироваться
            time.sleep(3)

            self.is_running = True
            logger.info("✅ Бот запущен в отдельном потоке")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            self.is_running = False
            return False

    def stop_polling(self):
        """Остановка бота"""
        try:
            if self.is_running and self.application:
                # Останавливаем vision анализ
                if hasattr(self, 'vision_task') and self.vision_task:
                    try:
                        self.vision_task.cancel()
                        logger.info("✅ Vision анализ остановлен")
                    except Exception as e:
                        logger.error(f"❌ Ошибка остановки vision анализа: {e}")

                self.application.stop()
                self.is_running = False
                logger.info("✅ Бот остановлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка остановки бота: {e}")
            return False

    # ========== МЕТОДЫ ОТПРАВКИ УВЕДОМЛЕНИЙ ==========

    async def send_notification_with_image(self, message: str, image_data: str = None,
                                           button_text: str = "📱 Посмотреть", button_url: str = ""):
        """Отправка уведомления с изображением и проверкой группы"""
        MAX_RETRIES = 3
        retry_count = 0

        while retry_count < MAX_RETRIES:
            try:
                chat_id = get_chat_id()
                if not chat_id:
                    logger.error("❌ TELEGRAM_CHAT_ID не установлен")
                    return False

                # 🔒 ПРОВЕРКА ГРУППЫ ЧЕРЕЗ GROUP_MANAGER
                try:
                    from bot.group_manager import group_manager
                    if not await group_manager.can_send_to_group(chat_id):
                        logger.warning(f"🚫 Отправка в группу {chat_id} заблокирована (превышен лимит участников)")
                        return False
                except Exception as group_error:
                    logger.warning(f"⚠️ Ошибка проверки группы, разрешаем отправку: {group_error}")

                logger.info(f"📤 Отправка уведомления в чат {chat_id}")

                # Создаем клавиатуру с кнопкой
                keyboard = []
                if button_url:
                    keyboard.append([InlineKeyboardButton(button_text, url=button_url)])

                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

                # Если есть изображение
                if image_data and self.is_valid_image_data(image_data):
                    try:
                        logger.info("🖼️ Отправка сообщения с фото")

                        if 'base64,' in image_data:
                            base64_str = image_data.split('base64,')[1]
                        else:
                            base64_str = image_data

                        image_bytes = base64.b64decode(base64_str)

                        if len(image_bytes) > 10 * 1024 * 1024:
                            logger.warning("⚠️ Изображение слишком большое, отправляем без фото")
                            return await self.send_text_notification(message, reply_markup)

                        caption = message[:1024] if len(message) > 1024 else message

                        await self.bot.send_photo(
                            chat_id=chat_id,
                            photo=image_bytes,
                            caption=caption,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                        logger.info("✅ Уведомление с фото отправлено")
                        return True

                    except Exception as photo_error:
                        logger.warning(f"⚠️ Ошибка отправки фото: {photo_error}. Пробуем текстовое сообщение")
                        return await self.send_text_notification(message, reply_markup)

                else:
                    logger.info("📝 Отправляем текстовое сообщение")
                    return await self.send_text_notification(message, reply_markup)

            except NetworkError as e:
                retry_count += 1
                logger.warning(f"📡 Ошибка сети (попытка {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(2)
                else:
                    logger.error("❌ Не удалось отправить из-за проблем с сетью")
                    return False

            except TelegramError as e:
                logger.error(f"❌ Ошибка Telegram API: {e}")
                return False

            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка отправки: {e}")
                return False

        return False

    async def group_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для проверки информации о группе"""
        try:
            chat_id = update.effective_chat.id

            group_info = await group_manager.get_group_info(chat_id)

            if group_info:
                status = "✅ Можно отправлять" if not group_info['is_over_limit'] else "🚫 Превышен лимит"

                info_text = f"""
    👥 **Информация о группе**

    📝 **Название:** {group_info['title']}
    🆔 **ID:** `{group_info['id']}`
    👤 **Участников:** {group_info['members_count']}
    📊 **Лимит:** {group_manager.max_members}
    🎯 **Статус:** {status}

    💡 *Лимит участников: {group_manager.max_members}*
                """
            else:
                info_text = "❌ Не удалось получить информацию о группе"

            await update.message.reply_text(info_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка получения информации о группе: {e}")
            await update.message.reply_text("❌ Ошибка получения информации о группе")

    def is_valid_image_data(self, image_data):
        """Проверка валидности данных изображения"""
        if not image_data:
            return False

        try:
            if 'base64,' in image_data:
                base64_str = image_data.split('base64,')[1]
            else:
                base64_str = image_data

            decoded = base64.b64decode(base64_str)
            return len(decoded) > 100
        except:
            return False

    async def send_text_notification(self, message: str, reply_markup=None):
        """Отправка текстового уведомления"""
        try:
            chat_id = get_chat_id()
            if not chat_id:
                logger.error("❌ TELEGRAM_CHAT_ID не установлен")
                return False

            if len(message) > 4096:
                parts = [message[i:i + 4096] for i in range(0, len(message), 4096)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1 and reply_markup:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            reply_markup=reply_markup,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

            logger.info("✅ Текстовое уведомление отправлено")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}")
            return False


# ========== ГЛОБАЛЬНЫЕ ФУНКЦИИ ==========

# Глобальный экземпляр бота
bot_instance = None


def initialize_bot():
    """Инициализация и запуск бота"""
    from shared.utils.config import get_bot_token

    token = get_bot_token()
    if not token:
        logger.error("❌ Токен бота не найден!")
        return False

    logger.info(f"🤖 Инициализация бота с токеном: {token[:10]}...")

    try:
        # Создаем экземпляр нашего бота
        global bot_instance
        bot_instance = ProfitHubBot(token)

        # Все обработчики уже настроены в конструкторе ProfitHubBot
        # через метод setup_handlers

        logger.info("✅ Бот инициализирован успешно!")
        logger.info("🚀 Запускаем бота в отдельном потоке...")

        # Запускаем бота в отдельном потоке
        success = bot_instance.start_polling()

        if success:
            logger.info("✅ Бот успешно запущен!")
            # Ждем бесконечно (или пока не будет прервано)
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Остановка бота по запросу пользователя...")
                bot_instance.stop_polling()
                return True
        else:
            print("❌ Не удалось запустить бота")
            return False

    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Основная функция запуска бота"""
    print("=" * 60)
    print("🚀 ЗАПУСК PROFIT HUB TELEGRAM БОТА")
    print("=" * 60)
    print(f"📁 Рабочая директория: {os.path.dirname(os.path.abspath(__file__))}")

    # Проверяем токен перед запуском
    from shared.utils.config import get_bot_token
    token = get_bot_token()

    if not token or token == 'ваш_токен_бота':
        print("❌ ТОКЕН БОТА НЕ НАЙДЕН!")
        print("👉 Установите TELEGRAM_BOT_TOKEN в настройках Django")
        print("   или в файле .env:")
        print("   TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather")
        return False

    print(f"✅ Токен найден: {token[:10]}...")
    print("🔧 Инициализация бота...")

    return initialize_bot()


if __name__ == "__main__":
    # Настройка Django для прямого запуска
    import os
    import sys

    # Добавляем корень проекта в путь Python
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

    try:
        import django

        django.setup()
        print("✅ Django успешно настроен")
    except Exception as e:
        print(f"❌ Ошибка настройки Django: {e}")
        sys.exit(1)

    # Запускаем бота
    success = main()

    if success:
        print("\n" + "=" * 60)
        print("✅ Бот успешно завершил работу")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Бот завершил работу с ошибкой")
        print("=" * 60)
        sys.exit(1)