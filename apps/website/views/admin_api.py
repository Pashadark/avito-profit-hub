"""
API для админ-панели
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from datetime import datetime

try:
    from ..data_collectors.admin_data import AdminDataCollector
    collector = AdminDataCollector()
except:
    collector = None


@require_GET
def admin_database_info(request):
    if collector:
        data = collector.get_postgresql_stats()
        return JsonResponse(data)
    return JsonResponse({
        'status': 'test',
        'database_size': '45.2 MB',
        'tables_count': 12,
        'total_records_count': 1247,
        'updated_at': datetime.now().isoformat()
    })


@require_GET
def admin_parser_stats(request):
    if collector:
        data = collector.get_parser_real_stats()
        return JsonResponse(data)
    return JsonResponse({
        'status': 'test',
        'stats': {
            'total_searches': 1247,
            'items_found': 8562,
            'good_deals_found': 342,
            'success_rate': 87
        },
        'updated_at': datetime.now().isoformat()
    })


@require_GET  
def admin_console_update(request):
    return JsonResponse({
        'status': 'success',
        'messages': [{
            'type': 'test',
            'timestamp': datetime.now().isoformat(),
            'message': '✅ Тестовое сообщение консоли',
            'level': 'info'
        }]
    })
