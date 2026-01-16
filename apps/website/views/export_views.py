# dashboard/views/export_views.py
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from ..utils.export_file import UniversalExporter
from ..models import FoundItem
import logging
import csv
import zipfile
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)


def get_all_user_items(request):
    """Получает ВСЕ товары пользователя (без фильтров)"""
    try:
        items = FoundItem.objects.filter(
            search_query__user=request.user
        ).select_related('search_query').order_by('-found_at')
        return items
    except Exception as e:
        logger.error(f"Error getting user items: {e}")
        return []


@login_required
def export_found_items_to_excel(request):
    """📊 Экспорт ВСЕХ данных в Excel"""
    try:
        items = get_all_user_items(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Нет данных для экспорта'}, status=400)

        exporter = UniversalExporter(items, request, 'all')
        return exporter.export_excel()
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def export_found_items_to_pdf(request):
    """📄 Экспорт ВСЕХ данных в PDF"""
    try:
        items = get_all_user_items(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Нет данных для экспорта'}, status=400)

        exporter = UniversalExporter(items, request, 'all')
        return exporter.export_pdf()
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def export_found_items_to_csv(request):
    """📝 Экспорт ВСЕХ данных в CSV"""
    try:
        items = get_all_user_items(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Нет данных для экспорта'}, status=400)

        exporter = UniversalExporter(items, request, 'all')
        return exporter.export_csv()
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def export_found_items_universal(request):
    """🎯 Универсальный экспорт ВСЕХ данных"""
    try:
        items = get_all_user_items(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Нет данных для экспорта'}, status=400)

        exporter = UniversalExporter(items, request, 'all')

        export_type = request.GET.get('type', 'excel')
        if export_type == 'excel':
            return exporter.export_excel()
        elif export_type == 'pdf':
            return exporter.export_pdf()
        elif export_type == 'csv':
            return exporter.export_csv()
        else:
            return JsonResponse({'status': 'error', 'message': 'Неверный тип'}, status=400)
    except Exception as e:
        logger.error(f"Export error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def export_all_zip(request):
    """📦 УНИВЕРСАЛЬНЫЙ ЭКСПОРТ - ВСЕ ФАЙЛЫ В ZIP"""
    try:
        items = get_all_user_items(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Нет данных для экспорта'}, status=400)

        # Создаем ZIP архив в памяти
        buffer = BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. Добавляем Excel файл
            excel_exporter = UniversalExporter(items, request, 'all')
            excel_response = excel_exporter.export_excel()
            zip_file.writestr(f"search_{timestamp}.xlsx", excel_response.content)

            # 2. Добавляем PDF файл
            pdf_exporter = UniversalExporter(items, request, 'all')
            pdf_response = pdf_exporter.export_pdf()
            zip_file.writestr(f"search_{timestamp}.pdf", pdf_response.content)

            # 3. Добавляем CSV файл
            csv_exporter = UniversalExporter(items, request, 'all')
            csv_response = csv_exporter.export_csv()
            zip_file.writestr(f"search_{timestamp}.csv", csv_response.content)

        buffer.seek(0)

        # Отдаем ZIP архив
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/zip'
        )

        response['Content-Disposition'] = f'attachment; filename="search_all_{timestamp}.zip"'
        response['Content-Length'] = len(buffer.getvalue())
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response

    except Exception as e:
        logger.error(f"ZIP export error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)