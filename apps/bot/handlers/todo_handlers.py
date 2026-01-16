import os
import sys

# ========== НАСТРОЙКА DJANGO ДЛЯ БЕЗОПАСНОГО ИМПОРТА ==========
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

try:
    import django
    if not django.conf.settings.configured:
        django.setup()
except Exception as e:
    print(f"⚠️ Не удалось настроить Django: {e}")
# ==============================================================

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from apps.website.models import TodoCard, TodoBoard, UserProfile

logger = logging.getLogger('bot.todo')


class TodoHandlers:
    def __init__(self, application):
        self.application = application
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков для задач"""
        self.application.add_handler(CommandHandler("todo", self.todo_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_task_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_todo_callback, pattern="^todo_"))

        logger.info("✅ Обработчики задач настроены")

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
        """Обработчик текстовых сообщений - создание задач"""
        user = update.effective_user
        text = update.message.text.strip()

        # Игнорируем короткие сообщения и команды
        if len(text) < 3 or text.startswith('/'):
            return

        user_profile = await sync_to_async(self._get_user_profile)(user.id)
        if not user_profile:
            return  # Не привязан - игнорируем

        # Создаем задачу
        task = await self.create_task(user_profile.user, text)

        if task:
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
        """Создать задачу"""
        try:
            # Разделяем заголовок и описание через |
            if '|' in text:
                title, description = text.split('|', 1)
                title = title.strip()
                description = description.strip()
            else:
                title = text
                description = ""

            # Получаем или создаем доску
            board, created = await sync_to_async(TodoBoard.objects.get_or_create)(
                user=user,
                defaults={'name': 'Мои задачи'}
            )

            task = await sync_to_async(TodoCard.objects.create)(
                board=board,
                title=title,
                description=description,
                status='todo',
                created_by=user
            )
            return task
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}")
            return None

    async def start_task(self, query, task_id, user):
        """Начать выполнение задачи"""
        try:
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

    async def get_user_tasks(self, user):
        """Получить задачи пользователя"""
        try:
            board = await sync_to_async(TodoBoard.objects.filter(user=user).first)()
            if not board:
                return []

            tasks = await sync_to_async(list)(
                TodoCard.objects.filter(board=board).order_by('-created_at')
            )

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

            return tasks_data
        except Exception as e:
            logger.error(f"Ошибка получения задач: {e}")
            return []

    def _get_user_profile(self, telegram_user_id):
        """Синхронный метод получения профиля"""
        try:
            return UserProfile.objects.filter(
                telegram_user_id=telegram_user_id,
                telegram_verified=True
            ).first()
        except Exception as e:
            logger.error(f"Ошибка получения профиля: {e}")
            return None


# Функция для настройки обработчиков
def setup_handlers(application):
    return TodoHandlers(application)