# dashboard/views/__init__.py
# Импортируем всё из views.py и search.py

from .views import *
from .search import *

# Для отладки можно добавить:
print("✅ Импортированы все функции из views.py и search.py")

# Импортируем функции экспорта из export_views.py
from .export_views import (
    export_found_items_to_excel,
    export_found_items_to_pdf,
    export_found_items_to_csv,
    export_found_items_universal,
    export_all_zip
)

from .ml_stats_views import (
    ml_dashboard,
    api_ml_stats,
    api_ml_test,
    api_ml_retrain,
)