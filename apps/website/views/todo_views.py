from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import json
import logging

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
            priority=data.get('priority', 2),  # Новый параметр приоритета
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
                'priority': card.priority,  # Добавляем приоритет
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
                'priority': card.priority,  # Добавляем приоритет
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