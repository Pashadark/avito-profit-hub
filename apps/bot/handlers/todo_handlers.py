"""
Обработчики задач
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from asgiref.sync import sync_to_async

from apps.bot.keyboards import (
    get_todo_main_keyboard,
    get_task_management_keyboard,
    get_task_list_keyboard,
    get_task_create_keyboard
)
from apps.bot.services.user_service import UserService

logger = logging.getLogger('bot.handlers.todo')


class TodoHandlers:
    """Обработчики задач"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def todo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /todo - управление задачами"""
        user = update.effective_user

        # Проверяем привязку аккаунта
        profile = await sync_to_async(UserService.get_user_profile)(user.id)
        if not profile:
            await update.message.reply_text(
                "❌ Сначала привяжите Telegram к аккаунту!\n\n"
                "Используйте команду /link или перейдите на сайт: "
                "http://127.0.0.1:8000/profile/"
            )
            return

        keyboard = get_todo_main_keyboard()

        await update.message.reply_text(
            "📋 **Управление задачами**\n\n"
            "Выберите действие или просто напишите задачу в чат!",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_todo_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback'ов для задач"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user = query.from_user

        logger.info(f"🔄 Обработка задачи: {callback_data} от {user.id}")

        # Проверяем привязку аккаунта
        profile = await sync_to_async(UserService.get_user_profile)(user.id)
        if not profile:
            await query.edit_message_text("❌ Сначала привяжите аккаунт через /link")
            return

        if callback_data == "todo_create":
            await self.show_create_dialog(query)
        elif callback_data == "todo_list":
            await self.show_task_list(query, profile.user)
        elif callback_data == "todo_active":
            await self.show_active_tasks(query, profile.user)
        elif callback_data == "todo_done":
            await self.show_done_tasks(query, profile.user)
        elif callback_data.startswith("todo_start_"):
            task_id = int(callback_data.replace("todo_start_", ""))
            await self.start_task(query, task_id, profile.user)
        elif callback_data.startswith("todo_complete_"):
            task_id = int(callback_data.replace("todo_complete_", ""))
            await self.complete_task(query, task_id, profile.user)
        elif callback_data.startswith("todo_delete_"):
            task_id = int(callback_data.replace("todo_delete_", ""))
            await self.delete_task(query, task_id, profile.user)
        else:
            await query.edit_message_text("⚙️ Команда в разработке")

    async def handle_task_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений - создание задач"""
        user = update.effective_user
        text = update.message.text.strip()

        # Игнорируем короткие сообщения и команды
        if len(text) < 3 or text.startswith('/'):
            return

        # Проверяем привязку аккаунта
        profile = await sync_to_async(UserService.get_user_profile)(user.id)
        if not profile:
            return  # Не привязан - игнорируем

        # Создаем задачу
        task = await self.create_task(profile.user, text)

        if task:
            keyboard = get_task_management_keyboard(task.id)

            await update.message.reply_text(
                f"✅ **Задача создана!**\n\n"
                f"📝 {task.title}\n"
                f"🏷️ Статус: К выполнению\n\n"
                f"Используйте кнопки ниже для управления:",
                reply_markup=keyboard,
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
            parse_mode='Markdown',
            reply_markup=get_task_create_keyboard()
        )

    async def show_task_list(self, query, user):
        """Показать список всех задач"""
        tasks = await self.get_user_tasks(user)

        if not tasks:
            await query.edit_message_text(
                "📝 У вас пока нет задач.\n\n"
                "Создайте первую задачу!",
                reply_markup=get_task_list_keyboard()
            )
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

            message += f"   [➡️](/todo_start_{task['id']}) [✅](/todo_complete_{task['id']}) [🗑️](/todo_delete_{task['id']})\n\n"

        keyboard = get_task_list_keyboard()

        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    async def show_active_tasks(self, query, user):
        """Показать активные задачи"""
        tasks = await self.get_user_tasks(user)
        active_tasks = [t for t in tasks if t['status'] in ['todo', 'in_progress']]

        if not active_tasks:
            await query.edit_message_text(
                "📝 Нет активных задач.\n\n"
                "Все задачи выполнены или не созданы.",
                reply_markup=get_task_list_keyboard()
            )
            return

        message = "⚡ **Активные задачи:**\n\n"
        for task in active_tasks[:10]:
            status_emoji = '🔄' if task['status'] == 'in_progress' else '⏳'
            message += f"{status_emoji} **{task['title']}**\n"
            message += f"   🏷️ {task['status_display']}\n\n"

        keyboard = get_task_list_keyboard()

        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_done_tasks(self, query, user):
        """Показать выполненные задачи"""
        tasks = await self.get_user_tasks(user)
        done_tasks = [t for t in tasks if t['status'] == 'done']

        if not done_tasks:
            await query.edit_message_text(
                "✅ Нет выполненных задач.\n\n"
                "Начните выполнять задачи!",
                reply_markup=get_task_list_keyboard()
            )
            return

        message = "✅ **Выполненные задачи:**\n\n"
        for task in done_tasks[:10]:
            completion_time = "Неизвестно"
            if task['completed_at']:
                completion_time = task['completed_at'].strftime('%d.%m.%Y %H:%M')

            message += f"✅ **{task['title']}**\n"
            message += f"   📅 Завершено: {completion_time}\n\n"

        keyboard = get_task_list_keyboard()

        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def create_task(self, user, text):
        """Создать задачу"""
        try:
            from apps.website.models import TodoCard, TodoBoard

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

            # Создаем задачу
            task = await sync_to_async(TodoCard.objects.create)(
                board=board,
                title=title,
                description=description,
                status='todo',
                created_by=user
            )

            logger.info(f"✅ Задача создана: {task.title} (ID: {task.id})")
            return task

        except Exception as e:
            logger.error(f"❌ Ошибка создания задачи: {e}")
            return None

    async def start_task(self, query, task_id, user):
        """Начать выполнение задачи"""
        try:
            from apps.website.models import TodoCard

            task = await sync_to_async(TodoCard.objects.get)(id=task_id, board__user=user)
            task.status = 'in_progress'
            await sync_to_async(task.save)()

            keyboard = get_task_management_keyboard(task.id)

            await query.edit_message_text(
                f"🔄 **Задача начата!**\n\n"
                f"📝 {task.title}\n"
                f"🏷️ Статус: В процессе\n\n"
                f"⏰ Время начала: {task.started_at.strftime('%d.%m.%Y %H:%M') if task.started_at else 'Сейчас'}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        except TodoCard.DoesNotExist:
            await query.edit_message_text("❌ Задача не найдена")
        except Exception as e:
            logger.error(f"Ошибка начала задачи: {e}")
            await query.edit_message_text("❌ Ошибка при начале задачи")

    async def complete_task(self, query, task_id, user):
        """Завершить задачу"""
        try:
            from apps.website.models import TodoCard

            task = await sync_to_async(TodoCard.objects.get)(id=task_id, board__user=user)
            task.status = 'done'
            await sync_to_async(task.save)()

            completion_time = task.get_completion_time()

            await query.edit_message_text(
                f"✅ **Задача выполнена!**\n\n"
                f"📝 {task.title}\n"
                f"🏷️ Статус: Выполнено\n"
                f"⏱️ Затрачено времени: {completion_time if completion_time else 'Неизвестно'}\n"
                f"📅 Завершено: {task.completed_at.strftime('%d.%m.%Y %H:%M') if task.completed_at else 'Сейчас'}",
                reply_markup=get_task_list_keyboard(),
                parse_mode='Markdown'
            )

        except TodoCard.DoesNotExist:
            await query.edit_message_text("❌ Задача не найдена")
        except Exception as e:
            logger.error(f"Ошибка завершения задачи: {e}")
            await query.edit_message_text("❌ Ошибка при завершении задачи")

    async def delete_task(self, query, task_id, user):
        """Удалить задачу"""
        try:
            from apps.website.models import TodoCard

            task = await sync_to_async(TodoCard.objects.get)(id=task_id, board__user=user)
            task_title = task.title
            await sync_to_async(task.delete)()

            await query.edit_message_text(
                f"🗑️ **Задача удалена:** {task_title}",
                reply_markup=get_task_list_keyboard(),
                parse_mode='Markdown'
            )

        except TodoCard.DoesNotExist:
            await query.edit_message_text("❌ Задача не найдена")
        except Exception as e:
            logger.error(f"Ошибка удаления задачи: {e}")
            await query.edit_message_text("❌ Ошибка при удалении задачи")

    async def get_user_tasks(self, user):
        """Получить задачи пользователя"""
        try:
            from apps.website.models import TodoBoard, TodoCard

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
            logger.error(f"❌ Ошибка получения задач: {e}")
            return []

    def register_handlers(self, application):
        """Регистрация обработчиков"""
        # Команды
        application.add_handler(CommandHandler("todo", self.todo_command))

        # Callback обработчики
        application.add_handler(CallbackQueryHandler(
            self.handle_todo_callback,
            pattern="^(todo_|todo_list|todo_create|todo_active|todo_done)"
        ))

        # Обработчик текстовых сообщений для создания задач
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_task_message
        ))

        logger.info("✅ Обработчики задач зарегистрированы")