# apps/website/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import hashlib
import os

from apps.website.models import TodoBoard, TodoCard

logger = logging.getLogger(__name__)


# ========== KANBAN TODO СИСТЕМА ==========

@login_required
def todo_kanban(request):
    """📋 Страница Kanban доски для задач

    🎯 Создание дефолтной доски если нет
    📊 Группировка карточек по статусу (todo/in_progress/done)
    ⭐ Сортировка по приоритету (критические → низкие)
    🔄 Перетаскивание карточек между колонками
    """
    board, created = TodoBoard.objects.get_or_create(
        user=request.user,
        defaults={'name': 'Моя доска задач'}
    )

    todo_cards = TodoCard.objects.filter(board=board, status='todo').order_by('-priority', 'card_order', 'created_at')
    in_progress_cards = TodoCard.objects.filter(board=board, status='in_progress').order_by('-priority', 'card_order',
                                                                                            'created_at')
    done_cards = TodoCard.objects.filter(board=board, status='done').order_by('-priority', 'card_order', 'created_at')

    context = {
        'board': board,
        'todo_cards': todo_cards,
        'in_progress_cards': in_progress_cards,
        'done_cards': done_cards,
    }
    return render(request, 'dashboard/todo_kanban.html', context)


@require_POST
@csrf_exempt
@login_required
def create_todo_card_api(request):
    """➕ Создание новой карточки через API

    📝 Создание карточки с заголовком, описанием и приоритетом
    🎯 Установка начального статуса и важности
    ⭐ Приоритет по умолчанию: 2 (Обычный)
    👤 Привязка к пользователю и доске
    """
    try:
        data = json.loads(request.body)
        board = TodoBoard.objects.get(user=request.user)

        card = TodoCard.objects.create(
            title=data.get('title', 'Новая задача'),
            description=data.get('description', ''),
            status=data.get('status', 'todo'),
            priority=data.get('priority', 2),
            task_type=data.get('task_type', 'other'),
            error_hash=data.get('error_hash', None),
            board=board,
            created_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'card': {
                'id': card.id,
                'title': card.title,
                'description': card.description,
                'status': card.status,
                'priority': card.priority,
                'task_type': card.task_type,
                'task_type_label': card.get_task_type_display(),
                'priority_label': card.priority_label,
                'priority_badge_color': card.priority_badge_color,
                'created_at': card.created_at.strftime('%d.%m.%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
def update_todo_card_status_api(request, card_id):
    """🔄 Обновление статуса карточки с учетом времени

    ⏰ Автоматическое обновление временных меток
    📊 Расчет времени выполнения
    🔄 Изменение статуса (todo → in_progress → done)
    """
    try:
        data = json.loads(request.body)
        card = TodoCard.objects.get(id=card_id, board__user=request.user)

        old_status = card.status
        new_status = data.get('status', card.status)

        card.status = new_status
        card.save()

        response_data = {
            'status': 'success',
            'time_info': {
                'completion_time': card.get_completion_time(),
                'current_time_in_progress': card.get_current_time_in_progress(),
                'is_in_progress': card.status == 'in_progress'
            }
        }

        return JsonResponse(response_data)

    except TodoCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Карточка не найдена'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
def delete_todo_card_api(request, card_id):
    """🗑️ Удаление карточки через API

    ⚠️ Удаление карточки по ID
    🔒 Проверка прав доступа к доске
    """
    try:
        card = TodoCard.objects.get(id=card_id, board__user=request.user)
        card.delete()

        return JsonResponse({'status': 'success'})
    except TodoCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Карточка не найдена'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
def update_todo_card_order_api(request):
    """🔢 Обновление порядка карточек через API

    📋 Изменение порядка карточек в колонке
    🎯 Обновление статуса и порядка одновременно
    🔄 Поддержка перетаскивания между колонками
    """
    try:
        data = json.loads(request.body)

        for item in data.get('items', []):
            card = TodoCard.objects.get(id=item['id'], board__user=request.user)
            card.status = item['status']
            card.card_order = item['order']
            card.save()

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
def update_todo_card_api(request, card_id):
    """✏️ Редактирование карточки через API

    📝 Изменение заголовка, описания и приоритета
    ⭐ Обновление важности задачи
    🔄 Сохранение изменений
    """
    try:
        data = json.loads(request.body)
        card = TodoCard.objects.get(id=card_id, board__user=request.user)

        card.title = data.get('title', card.title)
        card.description = data.get('description', card.description)

        # Обновляем приоритет если передан
        if 'priority' in data:
            card.priority = data.get('priority', card.priority)

        # Обновляем тип задачи если передан
        if 'task_type' in data:
            card.task_type = data.get('task_type', card.task_type)

        card.save()

        return JsonResponse({'status': 'success'})
    except TodoCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Карточка не найдена'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_http_methods(["GET"])
@login_required
def get_todo_card_api(request, card_id):
    """📄 Получение информации о карточке для редактирования

    🔍 Получение полных данных карточки включая приоритет
    ⭐ Получение важности задачи
    ⏰ Временные метки создания, начала, завершения
    🕒 Время выполнения задачи
    """
    try:
        card = TodoCard.objects.get(id=card_id, board__user=request.user)
        return JsonResponse({
            'status': 'success',
            'card': {
                'id': card.id,
                'title': card.title,
                'description': card.description,
                'status': card.status,
                'priority': card.priority,
                'task_type': card.task_type,
                'task_type_label': card.get_task_type_display(),
                'priority_label': card.priority_label,
                'priority_badge_color': card.priority_badge_color,
                'created_at': card.created_at.isoformat(),
                'started_at': card.started_at.isoformat() if card.started_at else None,
                'completed_at': card.completed_at.isoformat() if card.completed_at else None,
            }
        })
    except TodoCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Карточка не найдена'})


@require_http_methods(["GET"])
@login_required
def list_todo_cards_api(request):
    """📋 Получение списка задач пользователя через API

    🔍 Фильтрация по статусу
    📊 Возвращает все карточки пользователя с приоритетами
    ⭐ Включает данные о важности
    ⏰ Время выполнения задачи
    """
    try:
        status_filter = request.GET.get('status')
        board = TodoBoard.objects.filter(user=request.user).first()

        if not board:
            return JsonResponse({'status': 'success', 'cards': []})

        cards = TodoCard.objects.filter(board=board)

        if status_filter:
            cards = cards.filter(status=status_filter)

        cards_data = []
        for card in cards:
            cards_data.append({
                'id': card.id,
                'title': card.title,
                'description': card.description,
                'status': card.status,
                'priority': card.priority,
                'task_type': card.task_type,
                'task_type_label': card.get_task_type_display(),
                'priority_label': card.priority_label,
                'priority_badge_color': card.priority_badge_color,
                'created_at': card.created_at.isoformat(),
                'started_at': card.started_at.isoformat() if card.started_at else None,
                'completed_at': card.completed_at.isoformat() if card.completed_at else None,
                'completion_time': card.get_completion_time(),
            })

        return JsonResponse({'status': 'success', 'cards': cards_data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
def scan_logs_api(request):
    """🔍 Сканирование логов на ошибки и создание задач

    📁 Проверяет основные файлы логов
    🔍 Ищет ошибки и предупреждения
    🚫 Предотвращает дублирование через хэши
    📊 Возвращает количество созданных задач
    """
    try:
        user = request.user
        board = TodoBoard.objects.get(user=user)

        # Список лог-файлов для проверки
        log_files = [
            ('logs/system/system.log', 'system'),
            ('logs/django/django.log', 'django'),
            ('logs/bot/bot.log', 'bot'),
            ('logs/parsing/parsing.log', 'parser'),
            ('logs/website/website.log', 'website'),
            ('logs/apps/errors.log', 'apps'),
        ]

        tasks_created = 0
        errors_found = []

        for log_path, log_source in log_files:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-100:]  # Последние 100 строк каждой ошибки

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Определяем тип задачи по содержимому
                        task_type = 'other'
                        if any(word in line.lower() for word in ['error', 'exception', 'traceback', 'failed']):
                            if 'warning' in line.lower():
                                task_type = 'warning'
                            else:
                                task_type = 'error'

                            # Создаем хэш для предотвращения дублирования
                            error_hash = hashlib.sha256(line.encode()).hexdigest()

                            # Проверяем, нет ли уже такой ошибки
                            if TodoCard.objects.filter(error_hash=error_hash).exists():
                                continue

                            # Формируем заголовок и описание
                            title = f"[{log_source.upper()}] {line[:80]}..."
                            description = f"""
                            🚨 Обнаружена ошибка в логах

                            **Источник:** {log_source}
                            **Файл:** {log_path}
                            **Время обнаружения:** {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}

                            **Сообщение ошибки:**
                            ```
                            {line}
                            ```

                            ---
                            *Автоматически создано системой мониторинга логов*
                            """

                            # Определяем приоритет
                            priority = 4 if task_type == 'error' else 3

                            # Создаем задачу
                            try:
                                TodoCard.objects.create(
                                    board=board,
                                    title=title,
                                    description=description.strip(),
                                    status='todo',
                                    priority=priority,
                                    task_type=task_type,
                                    error_hash=error_hash,
                                    created_by=user
                                )
                                tasks_created += 1
                                errors_found.append({
                                    'source': log_source,
                                    'message': line[:100],
                                    'type': task_type
                                })
                            except Exception as create_error:
                                logger.error(f"Ошибка создания задачи из логов: {create_error}")

            except Exception as file_error:
                logger.error(f"Ошибка чтения файла {log_path}: {file_error}")
                continue

        return JsonResponse({
            'status': 'success',
            'tasks_created': tasks_created,
            'errors_found': errors_found,
            'message': f'Создано {tasks_created} задач из логов'
        })

    except TodoBoard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Доска задач не найдена'})
    except Exception as e:
        logger.error(f"Ошибка сканирования логов: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})