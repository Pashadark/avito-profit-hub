from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
import json
import logging
import asyncio
import threading
import time
from apps.website.console_manager import get_console_output, add_to_console, clear_console
from apps.website.log_viewer import log_viewer
from apps.website.models import (
    SearchQuery, FoundItem, ParserSettings, ParserStats
)
from apps.website.forms import ParserSettingsForm
from apps.website.console_manager import add_to_console
from apps.notifications.utils import notification_cache
from apps.notifications.services import ToastNotificationSystem

logger = logging.getLogger(__name__)


# ========== УПРАВЛЕНИЕ ПАРСЕРОМ ==========

def get_parser_status(request):
    """📊 Возвращает текущий статус парсера

    🔍 Проверяет доступность парсера
    🌐 Количество окон браузера
    ⏰ Статус таймера
    🔍 Активные поисковые запросы
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if not selenium_parser:
            return JsonResponse({
                'status': 'error',
                'message': 'Парсер не инициализирован'
            })

        is_running = getattr(selenium_parser, 'is_running', False)
        browser_windows = getattr(selenium_parser, 'browser_windows', 1)
        search_queries = getattr(selenium_parser, 'search_queries', [])

        drivers_count = 0
        browser_manager = getattr(selenium_parser, 'browser_manager', None)
        if browser_manager:
            drivers = getattr(browser_manager, 'drivers', [])
            drivers_count = len([d for d in drivers if d is not None])

        timer_manager = getattr(selenium_parser, 'timer_manager', None)
        timer_remaining = "Не установлен"
        timer_active = False

        if timer_manager:
            try:
                timer_status = timer_manager.get_timer_status()
                timer_remaining = timer_status.get('remaining', 'Не установлен')
                timer_active = timer_status.get('active', False)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения статуса таймера: {e}")
                timer_remaining = "Ошибка"

        status = {
            'is_running': is_running,
            'browser_windows': browser_windows,
            'drivers_count': drivers_count,
            'current_site': 'Avito',
            'timer_remaining': timer_remaining,
            'timer_active': timer_active,
            'search_queries_count': len(search_queries),
            'search_queries': search_queries[:3],
        }

        return JsonResponse({
            'status': 'success',
            'parser_status': status,
            'message': 'Статус загружен успешно'
        }, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        logger.error(f"❌ Критическая ошибка получения статуса парсера: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения статуса: {str(e)}'
        }, json_dumps_params={'ensure_ascii': False})


@require_http_methods(["POST"])
@csrf_exempt
def toggle_parser(request):
    """🔘 Запуск/остановка парсера через AJAX

    🚀 Запускает парсер в отдельном потоке
    🛑 Останавливает парсер синхронно
    🔄 Перезапускает парсер если нужно
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser
        import threading
        import time

        if selenium_parser.is_running:
            logger.info("🛑 Получен запрос на остановку парсера")

            def sync_stop():
                try:
                    selenium_parser.stop()
                    time.sleep(2)

                    if selenium_parser.is_running:
                        logger.warning("⚠️ Парсер не остановился, принудительная остановка")
                        selenium_parser.is_running = False

                        if hasattr(selenium_parser, 'browser_manager') and selenium_parser.browser_manager:
                            selenium_parser.browser_manager.close_drivers()

                    logger.info("✅ Парсер успешно остановлен")
                    return True

                except Exception as e:
                    logger.error(f"❌ Ошибка синхронной остановки: {e}")
                    try:
                        selenium_parser.is_running = False
                        if hasattr(selenium_parser, 'browser_manager') and selenium_parser.browser_manager:
                            selenium_parser.browser_manager.close_drivers()
                        return True
                    except:
                        return False

            stop_thread = threading.Thread(target=sync_stop, daemon=True)
            stop_thread.start()
            stop_thread.join(timeout=10)

            if stop_thread.is_alive():
                logger.warning("⚠️ Таймаут остановки, принудительно останавливаем")
                selenium_parser.is_running = False
                if hasattr(selenium_parser, 'browser_manager') and selenium_parser.browser_manager:
                    selenium_parser.browser_manager.close_drivers()

            logger.info("✅ Парсер успешно остановлен")
            return JsonResponse({
                'status': 'success',
                'message': '✅ Парсер успешно остановлен',
                'is_running': False
            })

        else:
            logger.info("🚀 Получен запрос на запуск парсера")

            if hasattr(selenium_parser, 'restart_parser'):
                restart_success = selenium_parser.restart_parser()
                if not restart_success:
                    return JsonResponse({
                        'status': 'error',
                        'message': '❌ Не удалось перезапустить парсер',
                        'is_running': False
                    })

            def start_parser_async():
                try:
                    import asyncio

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    if hasattr(selenium_parser, 'start_system'):
                        loop.run_until_complete(selenium_parser.start_system())
                    else:
                        loop.run_until_complete(selenium_parser.start())

                except Exception as e:
                    logger.error(f"❌ Ошибка при запуске парсера: {e}")
                finally:
                    try:
                        loop.close()
                    except:
                        pass

            parser_thread = threading.Thread(target=start_parser_async, daemon=True)
            parser_thread.start()

            time.sleep(2)

            logger.info("✅ Парсер запускается в фоновом режиме")
            return JsonResponse({
                'status': 'success',
                'message': '🚀 Парсер запускается...',
                'is_running': True
            })

    except Exception as e:
        logger.error(f"❌ Критическая ошибка переключения парсера: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'❌ Ошибка: {str(e)}'
        })


@require_POST
@csrf_exempt
@login_required
def launch_parser_with_params(request):
    """🚀 Запуск парсера с параметрами с уведомлениями"""
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        data = json.loads(request.body)
        timer_hours = data.get('timer_hours')
        browser_windows = data.get('browser_windows', 3)
        site = data.get('site', 'avito')
        city = data.get('city', 'Москва')  # 🔥 ДОБАВЛЯЕМ ПОЛУЧЕНИЕ ГОРОДА

        if not selenium_parser:
            # Показываем toast об ошибке
            ToastNotificationSystem.error(
                request,
                'Парсер не инициализирован',
                'Ошибка запуска',
                position='toast-top-right',
                timeOut=5000,
                template='materialize'
            )
            return JsonResponse({
                'status': 'error',
                'message': 'Парсер не инициализирован'
            })

        try:
            browser_windows = int(browser_windows)
            if browser_windows < 1 or browser_windows > 6:
                browser_windows = 3
        except (ValueError, TypeError):
            browser_windows = 3

        supported_sites = ['avito', 'auto.ru']
        if site not in supported_sites:
            site = 'avito'
            logger.warning(f"⚠️ Неподдерживаемый сайт, используем avito")

        selenium_parser.browser_windows = browser_windows
        selenium_parser.current_site = site

        # 🔥 УСТАНАВЛИВАЕМ ГОРОД В ПАРСЕРЕ
        if hasattr(selenium_parser, 'settings_manager'):
            selenium_parser.settings_manager.city = city
            logger.info(f"🏙️ Установлен город для парсера: {city}")

        # 🔥 Также устанавливаем город в текущих настройках
        from apps.parsing.core.settings_manager import SettingsManager
        settings_manager = SettingsManager.get_instance()
        settings_manager.city = city

        if timer_hours:
            try:
                timer_hours = int(timer_hours)
                if hasattr(selenium_parser, 'timer_manager'):
                    selenium_parser.timer_manager.set_timer(timer_hours)
                    logger.info(f"⏰ Таймер установлен: {timer_hours} часов")
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Неверный формат таймера: {e}")
                timer_hours = None
        else:
            if hasattr(selenium_parser, 'timer_manager'):
                selenium_parser.timer_manager.reset_timer()

        # Уведомление о запуске парсера
        site_display = "Auto.ru" if site == "auto.ru" else "Avito"
        timer_text = f"{timer_hours} часов" if timer_hours else "не установлен"

        # 🔥 ДОБАВЛЯЕМ ГОРОД В УВЕДОМЛЕНИЕ
        city_display = "всей России" if city in ['', 'Вся Россия'] else f"города {city}"
        notification_text = f'Парсер запускается для {site_display} {city_display}!'

        notification_cache.notify_parser_status(request, {
            'status': 'success',
            'message': notification_text,
            'items_found': 0,
            'duration': '0 минут'
        })

        logger.info(f"🎯 Запуск парсера с параметрами:")
        logger.info(f"   • Сайт: {site}")
        logger.info(f"   • Окна: {browser_windows}")
        logger.info(f"   • Город: {city}")  # 🔥 ДОБАВЛЯЕМ ГОРОД В ЛОГИ
        logger.info(f"   • Таймер: {timer_hours} часов" if timer_hours else "   • Таймер: не установлен")

        def run_parser():
            try:
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # 🔥 ПЕРЕДАЕМ ГОРОД В START_SYSTEM
                loop.run_until_complete(
                    selenium_parser.start_system(
                        timer_hours=timer_hours,
                        browser_windows=browser_windows,
                        site=site,
                        search_queries=None,
                        city=city  # 🔥 ПЕРЕДАЕМ ГОРОД
                    )
                )

            except Exception as e:
                logger.error(f"❌ Ошибка в потоке парсера для сайта {site}: {e}")
                # Уведомление об ошибке
                notification_cache.notify_parser_status(request, {
                    'status': 'error',
                    'message': f'Ошибка запуска парсера: {str(e)}',
                    'items_found': 0,
                    'duration': '0 минут'
                })
            finally:
                try:
                    loop.close()
                except:
                    pass

        if selenium_parser.is_running:
            # Уведомление, что парсер уже запущен
            ToastNotificationSystem.warning(
                request,
                f'Парсер уже запущен для сайта {site_display}',
                'Предупреждение',
                position='toast-top-right',
                timeOut=4000,
                template='materialize'
            )

            return JsonResponse({
                'status': 'warning',
                'message': f'Парсер уже запущен для сайта {site_display}'
            })

        import threading
        parser_thread = threading.Thread(target=run_parser, daemon=True)
        parser_thread.start()

        import time
        time.sleep(2)

        return JsonResponse({
            'status': 'success',
            'message': f'Парсер запускается для {site_display} {city_display}! Окна: {browser_windows}, Таймер: {timer_text}',
            'browser_windows': browser_windows,
            'timer_hours': timer_hours,
            'site': site,
            'city': city  # 🔥 ВОЗВРАЩАЕМ ГОРОД В ОТВЕТЕ
        })

    except Exception as e:
        logger.error(f"❌ Ошибка запуска парсера: {e}")
        # Уведомление об ошибке
        ToastNotificationSystem.error(
            request,
            f'Ошибка запуска: {str(e)}',
            'Ошибка парсера',
            position='toast-top-center',
            timeOut=6000,
            template='materialize'
        )

        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка запуска: {str(e)}'
        })


@login_required
def parser_status(request):
    """📡 Статус парсера с учетом сайта

    🔍 Получает статус из парсера
    🌐 Отображает текущий сайт
    📊 Возвращает все параметры работы
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if not selenium_parser:
            return JsonResponse({
                'status': 'error',
                'message': 'Парсер не инициализирован'
            })

        status_data = selenium_parser.get_parser_status()

        site_display = "Auto.ru" if status_data.get('current_site') == 'auto.ru' else "Avito"
        status_data['site_display'] = site_display

        return JsonResponse({
            'status': 'success',
            'parser_status': status_data
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса парсера: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка получения статуса: {str(e)}'
        })


@login_required
def force_parser_check(request):
    """🔍 Принудительная проверка парсером

    🚀 Запускает проверку цен в реальном времени
    📢 Отправляет уведомления если найдены выгодные предложения
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if selenium_parser.is_running:
            import threading
            import asyncio

            def run_check():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(selenium_parser.check_prices_and_notify())
                except Exception as e:
                    add_to_console(f"Ошибка принудительной проверки: {e}")
                finally:
                    if loop:
                        loop.close()

            thread = threading.Thread(target=run_check, daemon=True)
            thread.start()

            messages.success(request, '✅ Запущена принудительная проверка!')
        else:
            messages.warning(request, '⚠️ Парсер не запущен. Сначала запустите парсер.')

    except ImportError:
        messages.error(request, '❌ Парсер недоступен')

    return redirect('parser_settings')


# ========== НАСТРОЙКИ ПАРСЕРА ==========

@login_required
def parser_settings_view(request):
    """⚙️ Страница настроек парсера с историей

    📝 Управление множественными настройками
    🌐 Выбор сайта (avito/auto.ru)
    📊 Просмотр последней активности
    🔄 Сохранение и загрузка настроек
    """
    try:
        all_settings = ParserSettings.objects.filter(user=request.user).order_by('-is_default', '-updated_at')

        current_settings = all_settings.filter(is_default=True).first()
        if not current_settings and all_settings.exists():
            current_settings = all_settings.first()

        if not current_settings:
            current_settings = ParserSettings.objects.create(
                user=request.user,
                name='Основные настройки',
                keywords='Видеокарта, iPhone, кроссовки',
                min_price=0,
                max_price=100000,
                min_rating=4.0,
                seller_type='all',
                check_interval=30,
                max_items_per_hour=10,
                browser_windows=1,
                site='avito',
                is_active=True,
                is_default=True
            )
            all_settings = ParserSettings.objects.filter(user=request.user)

        recent_activities = FoundItem.objects.filter(
            search_query__user=request.user
        ).order_by('-found_at')[:10]

        parser_status = "остановлен"
        try:
            from apps.parsing.utils.selenium_parser import selenium_parser
            parser_status = "работает" if selenium_parser.is_running else "остановлен"
        except:
            parser_status = "недоступен"

        current_keywords = [k.strip() for k in current_settings.keywords.split(',') if
                            k.strip()] if current_settings.keywords else []

        form = ParserSettingsForm(instance=current_settings)
        current_settings_id = current_settings.id

        context = {
            'form': form,
            'all_settings': all_settings,
            'current_settings_id': current_settings_id,
            'recent_activities': recent_activities,
            'parser_status': parser_status,
            'current_keywords': current_keywords,
            'current_site': current_settings.site,
        }

        if request.method == 'POST':
            return handle_settings_post(request, current_settings)

        return render(request, 'dashboard/parser_settings.html', context)

    except Exception as e:
        messages.error(request, f'❌ Ошибка загрузки страницы: {str(e)}')
        return redirect('website:dashboard')


def handle_settings_post(request, current_settings):
    """🔄 Обработка POST запросов для настроек парсера

    💾 Сохранение настроек
    📂 Загрузка настроек
    🚀 Запуск с настройками
    🗑️ Удаление настроек
    """
    try:
        if 'save_settings' in request.POST:
            return save_settings(request, current_settings)

        elif 'load_settings' in request.POST:
            settings_id = request.POST.get('load_settings')
            return load_settings(request, settings_id)

        elif 'run_settings' in request.POST:
            settings_id = request.POST.get('run_settings')
            return run_with_settings(request, settings_id)

        elif 'delete_settings' in request.POST:
            settings_id = request.POST.get('delete_settings')
            return delete_settings(request, settings_id)

        return redirect('parser_settings')

    except Exception as e:
        messages.error(request, f'❌ Ошибка обработки запроса: {str(e)}')
        return redirect('parser_settings')


def save_settings(request, current_settings):
    """💾 Сохранение настроек парсера

    📝 Обновление всех полей настроек
    🌐 Сохранение выбранного сайта
    ⭐ Установка настроек по умолчанию
    🤖 Обновление парсера в реальном времени
    """
    try:
        current_settings.name = request.POST.get('name', 'Мои настройки')
        current_settings.keywords = request.POST.get('keywords', '')
        current_settings.min_price = float(request.POST.get('min_price', 0))
        current_settings.max_price = float(request.POST.get('max_price', 100000))
        current_settings.min_rating = float(request.POST.get('min_rating', 4.0))
        current_settings.seller_type = request.POST.get('seller_type', 'all')
        current_settings.check_interval = int(request.POST.get('check_interval', 30))
        current_settings.max_items_per_hour = int(request.POST.get('max_items_per_hour', 10))
        current_settings.browser_windows = int(request.POST.get('browser_windows', 1))
        current_settings.is_active = request.POST.get('is_active') == 'on'
        current_settings.is_default = request.POST.get('is_default') == 'on'
        current_settings.site = request.POST.get('site', 'avito')

        if current_settings.is_default:
            ParserSettings.objects.filter(user=request.user).exclude(id=current_settings.id).update(is_default=False)

        current_settings.save()

        update_parser_settings(current_settings)

        messages.success(request, '✅ Настройки сохранены и парсер обновлен!')
        return redirect('parser_settings')

    except Exception as e:
        messages.error(request, f'❌ Ошибка сохранения настроек: {str(e)}')
        return redirect('parser_settings')


def load_settings(request, settings_id):
    """📂 Загрузка настроек парсера

    🔍 Поиск настроек по ID
    ⭐ Установка как настроек по умолчанию
    🤖 Обновление парсера загруженными настройками
    """
    try:
        settings = ParserSettings.objects.get(id=settings_id, user=request.user)

        ParserSettings.objects.filter(user=request.user).update(is_default=False)
        settings.is_default = True
        settings.save()

        update_parser_settings(settings)

        messages.success(request, f'✅ Загружены настройки: {settings.name}')
        return redirect('parser_settings')

    except ParserSettings.DoesNotExist:
        messages.error(request, '❌ Настройки не найдены')
        return redirect('parser_settings')


def run_with_settings(request, settings_id):
    """🚀 Запуск парсера с конкретными настройками

    🔍 Получение настроек по ID
    🤖 Обновление парсера конкретными настройками
    🚀 Запуск парсера если он не работает
    """
    try:
        settings = ParserSettings.objects.get(id=settings_id, user=request.user)
        add_to_console(f"🚀 ЗАПУСК: Настройки '{settings.name}' с ключевыми словами: {settings.keywords}")

        update_success = update_parser_settings(settings)

        if update_success:
            try:
                from apps.parsing.utils.selenium_parser import selenium_parser

                if not selenium_parser.is_running:
                    import threading
                    import asyncio

                    def run_parser():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(selenium_parser.check_prices_and_notify())
                        except Exception as e:
                            add_to_console(f"Ошибка запуска парсера: {e}")
                        finally:
                            if loop:
                                loop.close()

                    thread = threading.Thread(target=run_parser, daemon=True)
                    thread.start()
                    messages.success(request, f'🚀 Парсер запущен с настройками: {settings.name}')
                    add_to_console(f"✅ Парсер запущен с ключевыми словами: {settings.keywords}")
                else:
                    messages.info(request, f'ℹ️ Настройки обновлены: {settings.name}. Парсер уже работает.')
                    add_to_console(f"ℹ️ Настройки обновлены для работающего парсера: {settings.keywords}")

            except Exception as e:
                messages.error(request, f'❌ Ошибка запуска парсера: {str(e)}')
                add_to_console(f"❌ Ошибка запуска парсера: {e}")
        else:
            messages.error(request, f'❌ Ошибка обновления настроек парсера')
            add_to_console(f"❌ Не удалось обновить настройки парсера")

        return redirect('parser_settings')

    except ParserSettings.DoesNotExist:
        messages.error(request, '❌ Настройки не найдены')
        return redirect('parser_settings')


def delete_settings(request, settings_id):
    """🗑️ Удаление настроек парсера

    ⚠️ Проверяет что это не последние настройки
    🔒 Удаляет только если есть другие настройки
    """
    try:
        settings = ParserSettings.objects.get(id=settings_id, user=request.user)

        if ParserSettings.objects.filter(user=request.user).count() > 1:
            settings.delete()
            messages.success(request, f'✅ Настройки "{settings.name}" удалены')
        else:
            messages.error(request, '❌ Нельзя удалить последние настройки')

        return redirect('parser_settings')

    except ParserSettings.DoesNotExist:
        messages.error(request, '❌ Настройки не найдены')
        return redirect('parser_settings')


def update_parser_settings(settings):
    """🔄 Обновление настроек парсера в реальном времени

    🤖 Передает настройки в работающий парсер
    🌐 Устанавливает сайт для парсинга
    🔧 Использует правильный метод обновления
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        settings_data = {
            'browser_windows': settings.browser_windows,
            'keywords': settings.keywords,
            'exclude_keywords': settings.exclude_keywords or '',
            'min_price': settings.min_price,
            'max_price': settings.max_price,
            'min_rating': settings.min_rating,
            'seller_type': settings.seller_type,
            'check_interval': settings.check_interval,
            'max_items_per_hour': settings.max_items_per_hour,
            'site': settings.site
        }

        print(f"🔧 UPDATE PARSER SETTINGS: site={settings.site}, keywords={settings.keywords}")

        if hasattr(selenium_parser, 'update_settings'):
            success = selenium_parser.update_settings(settings_data)
        else:
            selenium_parser.search_queries = [k.strip() for k in settings.keywords.split(',') if k.strip()]
            selenium_parser.min_price = settings.min_price
            selenium_parser.max_price = settings.max_price
            selenium_parser.min_rating = settings.min_rating
            selenium_parser.seller_type = settings.seller_type
            selenium_parser.current_site = settings.site
            success = True

        if success:
            print(f"✅ Настройки парсера обновлены: {settings.keywords}, сайт: {settings.site}")
        else:
            print(f"❌ Ошибка обновления настроек парсера")

        return success

    except Exception as e:
        print(f"❌ Критическая ошибка обновления парсера: {e}")
        return False


@require_POST
@csrf_exempt
@login_required
def ajax_save_settings(request):
    """💾 AJAX сохранение настроек парсера

    🔄 Обновление существующих настроек
    🆕 Создание новых настроек
    🌐 Сохранение выбранного сайта
    🤖 Применение настроек в парсере
    """
    try:
        user = request.user
        settings_id = request.POST.get('settings_id')
        site = request.POST.get('site', 'avito')

        print(f"🔧 DEBUG AJAX SAVE: site={site}, settings_id={settings_id}")
        print(f"🔧 DEBUG AJAX SAVE: все POST данные: {dict(request.POST)}")

        add_to_console(f"💾 СОХРАНЕНИЕ НАСТРОЕК: user={user}, settings_id={settings_id}")

        is_default = request.POST.get('is_default') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        post_data = request.POST.copy()

        numeric_fields = ['min_price', 'max_price', 'min_rating', 'check_interval', 'max_items_per_hour',
                          'browser_windows']
        for field in numeric_fields:
            if not post_data.get(field):
                if field in ['min_price', 'max_price']:
                    post_data[field] = '0'
                elif field == 'min_rating':
                    post_data[field] = '4.0'
                elif field == 'check_interval':
                    post_data[field] = '30'
                elif field == 'max_items_per_hour':
                    post_data[field] = '10'
                elif field == 'browser_windows':
                    post_data[field] = '1'

        if settings_id and settings_id not in ['', 'None']:
            try:
                instance = ParserSettings.objects.get(id=settings_id, user=user)
                form = ParserSettingsForm(post_data, instance=instance)
                add_to_console(f"📝 ОБНОВЛЕНИЕ существующих настроек: {instance.name}")
            except ParserSettings.DoesNotExist:
                print("❌ Настройки не найдены, создаем новые")
                form = ParserSettingsForm(post_data)
        else:
            print("🆕 СОЗДАНИЕ новых настроек")
            form = ParserSettingsForm(post_data)

        if form.is_valid():
            settings = form.save(commit=False)
            settings.user = user
            settings.is_default = is_default
            settings.is_active = is_active
            settings.save()

            add_to_console(f"✅ Настройки сохранены: {settings.name}, ID: {settings.id}")

            if settings.is_default:
                ParserSettings.objects.filter(user=user).exclude(id=settings.id).update(is_default=False)
                print("⭐ Настройки установлены как основные по умолчанию")

            try:
                from apps.parsing.utils.selenium_parser import selenium_parser
                settings_data = {
                    'browser_windows': settings.browser_windows,
                    'keywords': settings.keywords,
                    'exclude_keywords': settings.exclude_keywords or '',
                    'min_price': settings.min_price,
                    'max_price': settings.max_price,
                    'min_rating': settings.min_rating,
                    'seller_type': settings.seller_type,
                    'check_interval': settings.check_interval,
                    'max_items_per_hour': settings.max_items_per_hour
                }

                if hasattr(selenium_parser, 'update_settings'):
                    selenium_parser.update_settings(settings_data)
                    print("🤖 Настройки применены в парсере")
                else:
                    print("⚠️ Парсер не имеет метода update_settings")

            except Exception as e:
                add_to_console(f"⚠️ Ошибка обновления парсера: {e}")

            return JsonResponse({
                'status': 'success',
                'message': 'Настройки сохранены и применены',
                'settings_id': settings.id
            })
        else:
            add_to_console(f"❌ Ошибки валидации формы:")
            for field, errors in form.errors.items():
                add_to_console(f"   {field}: {errors}")

            error_messages = []
            for field, errors in form.errors.items():
                field_name = dict(form.fields).get(field).label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_name}: {error}")

            return JsonResponse({
                'status': 'error',
                'message': 'Ошибки в данных формы',
                'errors': form.errors.get_json_data(),
                'error_messages': error_messages
            })

    except Exception as e:
        add_to_console(f"❌ Критическая ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()

        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка сохранения: {str(e)}'
        })
# ========== ДИАГНОСТИКА И ОТЛАДКА ==========

@login_required
def debug_settings(request):
    """🔧 Расширенная страница отладки

    ⚙️ Просмотр текущих настроек парсера
    🔍 Проверка доступности парсера
    🗄️ Проверка подключения к базе данных
    📋 Консольный вывод системы
    """
    add_to_console(f"🔧 Пользователь: {request.user} зашел в настройки отладки")

    settings = ParserSettings.objects.filter(user=request.user).first()

    if not settings:
        settings = ParserSettings.objects.create(
            user=request.user,
            keywords="Видеокарта, iPhone, кроссовки",
            min_price=0,
            max_price=100000,
            min_rating=4.0,
            seller_type='all',
            check_interval=30,
            max_items_per_hour=10,
            is_active=True
        )
        add_to_console(f"✅ Созданы настройки по умолчанию для пользователя {request.user}")

    console_data = get_console_output(50)

    parser_available = False
    parser_status = "недоступен"
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser
        parser_available = True
        parser_status = "работает" if selenium_parser.is_running else "остановлен"
        add_to_console(f"🤖 Парсер: {parser_status}")
    except Exception as e:
        add_to_console(f"❌ Ошибка доступа к парсеру: {e}")

    from django.db import connection
    db_connected = False
    try:
        connection.ensure_connection()
        db_connected = True
        add_to_console(f"✅ База данных подключена")
    except Exception as e:
        add_to_console(f"❌ Ошибка базы данных: {e}")

    keywords_list = []
    if settings and settings.keywords:
        keywords_list = [keyword.strip() for keyword in settings.keywords.split(',') if keyword.strip()]
        add_to_console(f"🔍 Загружены ключевые слова: {keywords_list}")

    context = {
        'settings': settings,
        'current_time': timezone.now(),
        'parser_status': parser_status,
        'parser_available': parser_available,
        'db_connected': db_connected,
        'search_queries_count': len(keywords_list),
        'keywords_list': keywords_list,
        'debug_json': json.dumps({
            'keywords': settings.keywords if settings else None,
            'min_price': float(settings.min_price) if settings else 0,
            'max_price': float(settings.max_price) if settings else 0,
            'min_rating': float(settings.min_rating) if settings else 0,
            'seller_type': settings.seller_type if settings else 'all'
        }) if settings else '{}',
        'console_output': console_data,
        'log_files': log_viewer.log_files if hasattr(log_viewer, 'log_files') else [],
    }
    return render(request, 'dashboard/debug_settings.html', context)

@require_http_methods(["GET"])
def test_parser(request):
    """🤖 Тестирование соединения с парсером

    🔍 Проверка доступности парсера
    📊 Получение статуса работы
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        status = selenium_parser.get_status()
        return JsonResponse({
            'status': 'success',
            'message': f'Парсер доступен. Статус: {"работает" if status["is_running"] else "остановлен"}',
            'parser_status': status
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Парсер недоступен: {str(e)}'
        })


@login_required
def test_settings(request):
    """⚙️ Тест загрузки настроек

    🔍 Проверка существования настроек пользователя
    ✅ Возврат успешного статуса если настройки найдены
    """
    try:
        settings = ParserSettings.objects.filter(user=request.user).first()
        if settings:
            add_to_console(f"✅ Тест настроек: OK - {settings.keywords}")
            return JsonResponse({'status': 'success', 'message': 'Настройки загружены'})
        else:
            add_to_console(f"❌ Тест настроек: настройки не найдены")
            return JsonResponse({'status': 'error', 'message': 'Настройки не найдены'})
    except Exception as e:
        add_to_console(f"❌ Тест настроек: ошибка - {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def quick_update_settings(request):
    """⚡ Быстрое обновление ключевых слов

    📝 Обновление только поля keywords в настройках
    🤖 Синхронизация с работающим парсером
    """
    if request.method == 'POST':
        try:
            user = request.user
            if not user:
                messages.error(request, '❌ Пользователь не найден')
                return redirect('debug_settings')

            settings, created = ParserSettings.objects.get_or_create(
                user=user,
                defaults={
                    'keywords': 'Видеокарта, iPhone, кроссовки',
                    'min_price': 0,
                    'max_price': 100000,
                    'min_rating': 4.0,
                    'seller_type': 'all',
                    'check_interval': 30,
                    'max_items_per_hour': 10,
                    'is_active': True
                }
            )

            new_keywords = request.POST.get('keywords', '').strip()

            if not new_keywords:
                messages.error(request, '❌ Введите ключевые слова')
                return redirect('debug_settings')

            settings.keywords = new_keywords
            settings.save()

            add_to_console(f"⚡ Быстрое обновление: {new_keywords}")

            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT keywords, user_id FROM website_parsersettings WHERE user_id = %s", [user.id])
            db_result = cursor.fetchone()

            try:
                from apps.parsing.utils.selenium_parser import selenium_parser

                keywords_list = [keyword.strip() for keyword in new_keywords.split(',') if keyword.strip()]

                if hasattr(selenium_parser, 'search_queries'):
                    selenium_parser.search_queries = keywords_list
                    add_to_console(f"🤖 Парсер обновлен: {keywords_list}")
                    messages.success(request, f'✅ Обновлено! База: {new_keywords} | Парсер: {keywords_list}')
                else:
                    messages.success(request, f'✅ Сохранено в базу: {new_keywords}')

            except Exception as e:
                messages.success(request, f'✅ Сохранено в базу: {new_keywords} | Ошибка парсера: {str(e)}')

        except Exception as e:
            messages.error(request, f'❌ Критическая ошибка: {str(e)}')
            add_to_console(f"❌ Критическая ошибка: {str(e)}")

    return redirect('debug_settings')


@login_required
def force_reload_all_settings(request):
    """🔄 Принудительная перезагрузка ВСЕХ настроек из базы

    📥 Загрузка всех полей настроек из базы
    🤖 Обновление всех параметров в парсере
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        user = request.user
        settings = ParserSettings.objects.get(user=user)

        update_data = {
            'keywords': settings.keywords,
            'min_price': settings.min_price,
            'max_price': settings.max_price,
            'min_rating': settings.min_rating,
            'seller_type': settings.seller_type,
            'check_interval': settings.check_interval,
            'max_items_per_hour': settings.max_items_per_hour
        }

        if hasattr(selenium_parser, 'update_settings'):
            success = selenium_parser.update_settings(update_data)
        else:
            selenium_parser.search_queries = [k.strip() for k in settings.keywords.split(',') if k.strip()]
            selenium_parser.min_price = settings.min_price
            selenium_parser.max_price = settings.max_price
            selenium_parser.min_rating = settings.min_rating
            selenium_parser.seller_type = settings.seller_type
            success = True

        add_to_console(f"🔄 Перезагружены все настройки: {settings.keywords}")
        return JsonResponse({
            'status': 'success' if success else 'error',
            'message': f'Все настройки перезагружены: {settings.keywords}' if success else 'Ошибка обновления парсера'
        })

    except Exception as e:
        add_to_console(f"❌ Ошибка перезагрузки настроек: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def fix_database(request):
    """🔧 Исправление базы данных - синхронизация с парсером

    🔄 Создание настроек из данных работающего парсера
    💾 Сохранение ключевых слов парсера в базу
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        user = request.user
        if not user:
            return JsonResponse({'status': 'error', 'message': 'Пользователь не найден'})

        parser_keywords = ', '.join(selenium_parser.search_queries) if hasattr(selenium_parser,
                                                                               'search_queries') else ''

        settings, created = ParserSettings.objects.get_or_create(
            user=user,
            defaults={'keywords': parser_keywords}
        )

        if not created:
            settings.keywords = parser_keywords
            settings.save()

        add_to_console(f"🔧 Исправлена база: {parser_keywords}")
        return JsonResponse({
            'status': 'success',
            'message': f'База синхронизирована с парсером: {parser_keywords}',
            'action': 'created' if created else 'updated'
        })

    except Exception as e:
        add_to_console(f"❌ Ошибка исправления базы: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def force_load_all_settings(request):
    """📥 Принудительная загрузка всех настроек из базы

    🔄 Загрузка всех параметров в работающий парсер
    🤖 Обновление поисковых запросов, цен, рейтингов
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        user = request.user
        if not user:
            return JsonResponse({'status': 'error', 'message': 'Пользователь не найден'})

        settings = ParserSettings.objects.get(user=user)

        if hasattr(selenium_parser, 'search_queries'):
            selenium_parser.search_queries = [k.strip() for k in settings.keywords.split(',') if k.strip()]

        if hasattr(selenium_parser, 'min_price'):
            selenium_parser.min_price = settings.min_price

        if hasattr(selenium_parser, 'max_price'):
            selenium_parser.max_price = settings.max_price

        if hasattr(selenium_parser, 'min_rating'):
            selenium_parser.min_rating = settings.min_rating

        if hasattr(selenium_parser, 'seller_type'):
            selenium_parser.seller_type = settings.seller_type

        add_to_console(f"📥 Загружены все настройки: {selenium_parser.search_queries}")
        return JsonResponse({
            'status': 'success',
            'message': f'Все настройки загружены: {selenium_parser.search_queries}'
        })

    except Exception as e:
        add_to_console(f"❌ Ошибка загрузки настроек: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def get_parser_settings(request):
    """🔍 Получение текущих настроек парсера

    📊 Возврат текущих параметров работающего парсера
    🔍 Проверка доступности атрибутов парсера
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if not hasattr(selenium_parser, 'search_queries'):
            return JsonResponse({
                'status': 'error',
                'message': 'Парсер не имеет атрибута search_queries'
            })

        settings = {
            'keywords': ', '.join(selenium_parser.search_queries),
            'is_running': selenium_parser.is_running,
            'min_price': getattr(selenium_parser, 'min_price', 'N/A'),
            'max_price': getattr(selenium_parser, 'max_price', 'N/A'),
            'min_rating': getattr(selenium_parser, 'min_rating', 'N/A'),
            'seller_type': getattr(selenium_parser, 'seller_type', 'N/A')
        }

        return JsonResponse({'status': 'success', 'settings': settings})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def force_reload_settings(request):
    """🔄 Принудительная перезагрузка настроек

    🔄 Попытка использовать метод load_search_queries парсера
    💾 Запасной вариант - загрузка из базы данных
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if hasattr(selenium_parser, 'load_search_queries'):
            result = selenium_parser.load_search_queries()
            add_to_console(f"🔄 Перезагружены настройки: {selenium_parser.search_queries}")
            return JsonResponse({
                'status': 'success',
                'message': f'Настройки перезагружены: {selenium_parser.search_queries}'
            })
        else:
            user = request.user
            if user:
                try:
                    settings = ParserSettings.objects.get(user=user)
                    if settings.keywords:
                        selenium_parser.search_queries = [
                            keyword.strip() for keyword in settings.keywords.split(',') if keyword.strip()
                        ]
                        add_to_console(f"🔄 Настройки перезагружены: {selenium_parser.search_queries}")
                        return JsonResponse({
                            'status': 'success',
                            'message': f'Настройки перезагружены: {selenium_parser.search_queries}'
                        })
                except:
                    pass

            return JsonResponse({
                'status': 'error',
                'message': 'Метод load_search_queries не найден и не удалось перезагрузить настройки'
            })

    except Exception as e:
        add_to_console(f"❌ Ошибка перезагрузки: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_GET
@login_required
def debug_parser_settings(request):
    """🔍 Диагностика настроек парсера

    🔄 Сравнение настроек в базе и в работающем парсере
    📊 Проверка синхронизации данных
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser
        from apps.website.models import ParserSettings

        user = request.user

        parser_settings = ParserSettings.objects.filter(user=user).order_by('-is_default', '-updated_at').first()

        parser_current = {
            'search_queries': selenium_parser.search_queries,
            'browser_windows': selenium_parser.browser_windows,
            'is_running': selenium_parser.is_running
        }

        return JsonResponse({
            'status': 'success',
            'database_settings': {
                'exists': parser_settings is not None,
                'keywords': parser_settings.keywords if parser_settings else 'None',
                'browser_windows': parser_settings.browser_windows if parser_settings else 'None',
                'name': parser_settings.name if parser_settings else 'None'
            },
            'parser_current': parser_current,
            'message': 'Диагностика завершена'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка диагностики: {str(e)}'
        })


@require_GET
@login_required
def parser_diagnostics(request):
    """🔧 Диагностика парсера

    🔍 Проверка всех компонентов парсера
    🤖 Проверка browser_manager и timer_manager
    📊 Детальная информация о состоянии парсера
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        diagnostics = {
            'parser_module_loaded': 'selenium_parser' in globals(),
            'parser_instance_exists': selenium_parser is not None,
        }

        if selenium_parser:
            diagnostics.update({
                'is_running': getattr(selenium_parser, 'is_running', False),
                'browser_windows': getattr(selenium_parser, 'browser_windows', 0),
                'browser_manager_exists': hasattr(selenium_parser, 'browser_manager'),
                'timer_manager_exists': hasattr(selenium_parser, 'timer_manager'),
                'search_queries': getattr(selenium_parser, 'search_queries', []),
            })

            if hasattr(selenium_parser, 'browser_manager'):
                bm = selenium_parser.browser_manager
                diagnostics.update({
                    'browser_manager_drivers_count': len(getattr(bm, 'drivers', [])),
                    'browser_manager_setup_called': hasattr(bm, 'setup_drivers'),
                })

        return JsonResponse({
            'status': 'success',
            'diagnostics': diagnostics
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка диагностики: {str(e)}'
        })


@csrf_exempt
def test_settings_api(request):
    """🧪 Тестирование настроек

    🔍 Проверка работы парсера
    📊 Возврат статуса парсера
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser
        if selenium_parser.is_running:
            status = "работает"
        else:
            status = "не работает"

        return JsonResponse({
            'status': 'success',
            'message': f'Парсер {status}. Настройки загружены корректно.'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })
def health_parser(request):
    """🤖 Проверка здоровья парсера

    🔍 Проверяет инициализацию парсера
    📊 Возвращает статус работы
    🌐 Количество окон браузера
    🔍 Активные поисковые запросы
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        if selenium_parser and hasattr(selenium_parser, 'is_running'):
            status = 'healthy' if selenium_parser.is_running else 'warning'
            message = f'Парсер {"работает" if selenium_parser.is_running else "остановлен"}'

            browser_windows = getattr(selenium_parser, 'browser_windows', 0)
            search_queries = getattr(selenium_parser, 'search_queries', [])

            return JsonResponse({
                'status': status,
                'message': message,
                'is_running': selenium_parser.is_running,
                'browser_windows': browser_windows,
                'active_queries_count': len(search_queries),
                'details': 'Парсер инициализирован с настройками Django'
            })
        else:
            return JsonResponse({
                'status': 'warning',
                'message': 'Парсер не инициализирован'
            })

    except ImportError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка импорта парсера: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка парсера: {str(e)}'
        }, status=500)

def parser_stats_history(request):
    """📜 Получает историю статистики парсера

    📊 Последние 10 записей статистики
    🎯 Расчет успешности и эффективности
    """
    try:
        history = ParserStats.objects.all().order_by('-created_at')[:10]

        history_data = []
        for stat in history:
            history_data.append({
                'total_searches': stat.total_searches,
                'successful_searches': stat.successful_searches,
                'items_found': stat.items_found,
                'good_deals_found': stat.good_deals_found,
                'duplicates_blocked': stat.duplicates_blocked,
                'success_rate': stat.success_rate(),
                'efficiency_rate': stat.efficiency_rate(),
                'duplicate_rate': stat.duplicate_rate(),
                'created_at': stat.created_at.strftime('%d.%m.%Y %H:%M')
            })

        return history_data
    except Exception as e:
        add_to_console(f"❌ Ошибка получения истории статистики: {e}")
        return []

def get_cities_list(request):
    """
    API endpoint для получения списка всех городов из city_translator.py
    URL: /api/get-cities/
    Метод: GET
    """
    try:
        # 🔥 Пробуем импортировать из city_translator.py
        try:
            from apps.parsing.utils.city_translator import CITY_MAPPING
            cities = sorted(list(CITY_MAPPING.keys()))  # Сортируем по алфавиту

            return JsonResponse({
                'status': 'success',
                'cities': cities,
                'total': len(cities),
                'source': 'city_translator.py'
            })
        except ImportError as e:
            # 🔥 Если нет city_translator, используем backup файл
            json_path = os.path.join(settings.BASE_DIR, 'apps', 'parsing', 'utils', 'cities_backup.json')

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cities_data = json.load(f)
                    cities = sorted(list(cities_data.keys()))

                    return JsonResponse({
                        'status': 'success',
                        'cities': cities,
                        'total': len(cities),
                        'source': 'cities_backup.json'
                    })
            else:
                # 🔥 Если и backup нет, возвращаем основные города
                basic_cities = sorted([
                    'Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань',
                    'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону',
                    'Уфа', 'Красноярск', 'Воронеж', 'Пермь', 'Волгоград', 'Краснодар',
                    'Сочи', 'Пенза', 'Тюмень', 'Ижевск', 'Иркутск', 'Ульяновск',
                    'Хабаровск', 'Владивосток', 'Ярославль', 'Махачкала', 'Томск',
                    'Оренбург', 'Кемерово', 'Астрахань', 'Рязань', 'Набережные Челны',
                    'Липецк', 'Тула', 'Киров', 'Чебоксары', 'Калининград', 'Курск',
                    'Улан-Удэ', 'Ставрополь', 'Магнитогорск', 'Тверь', 'Севастополь',
                    'Сургут', 'Брянск', 'Иваново', 'Белгород', 'Симферополь',
                    # Краснодарский край
                    'Анапа', 'Армавир', 'Геленджик', 'Ейск', 'Новороссийск', 'Туапсе',
                    'Апшеронск', 'Белореченск', 'Горячий Ключ', 'Кропоткин', 'Крымск',
                    'Лабинск', 'Славянск-на-Кубани', 'Тимашёвск', 'Тихорецк', 'Абинск',
                ])

                return JsonResponse({
                    'status': 'success',
                    'cities': basic_cities,
                    'total': len(basic_cities),
                    'source': 'basic_list'
                })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'cities': [],
            'total': 0
        })

@require_http_methods(["GET"])
def test_parser(request):
    """🤖 Тестирование соединения с парсером

    🔍 Проверка доступности парсера
    📊 Получение статуса работы
    """
    try:
        from apps.parsing.utils.selenium_parser import selenium_parser

        status = selenium_parser.get_status()
        return JsonResponse({
            'status': 'success',
            'message': f'Парсер доступен. Статус: {"работает" if status["is_running"] else "остановлен"}',
            'parser_status': status
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Парсер недоступен: {str(e)}'
        })


@login_required
def test_settings(request):
    """⚙️ Тест загрузки настроек

    🔍 Проверка существования настроек пользователя
    ✅ Возврат успешного статуса если настройки найдены
    """
    try:
        settings = ParserSettings.objects.filter(user=request.user).first()
        if settings:
            add_to_console(f"✅ Тест настроек: OK - {settings.keywords}")
            return JsonResponse({'status': 'success', 'message': 'Настройки загружены'})
        else:
            add_to_console(f"❌ Тест настроек: настройки не найдены")
            return JsonResponse({'status': 'error', 'message': 'Настройки не найдены'})
    except Exception as e:
        add_to_console(f"❌ Тест настроек: ошибка - {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def start_parser_with_settings(request):
    """🚀 Запуск парсера с конкретными настройками"""
    try:
        settings_id = request.POST.get('settings_id')
        site = request.POST.get('site', 'avito')

        logger.info(f"🔍 Получен сайт из запроса: {site}")

        # Получаем выбранные настройки
        settings = get_object_or_404(ParserSettings, id=settings_id, user=request.user)
        logger.info(f"✅ Настройки получены: {settings.name} для пользователя {request.user.username}")
        logger.info(f"🏙️ Город в настройках: '{settings.city}'")

        # 🔥 **КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 1: Активируем ВЫБРАННЫЕ настройки**
        try:
            with transaction.atomic():
                # Деактивируем ВСЕ настройки пользователя
                ParserSettings.objects.filter(user_id=request.user.id).update(is_active=False)

                # Активируем ВЫБРАННЫЕ настройки
                settings.is_active = True
                settings.save()

                logger.info(f"🔥 Настройки '{settings.name}' АКТИВИРОВАНЫ (город: {settings.city})")
        except Exception as e:
            logger.error(f"❌ Ошибка активации настроек: {e}")

        from apps.parsing.utils.selenium_parser import selenium_parser

        # 🔥 **КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 2: ОЧИЩАЕМ КЭШ ПАРСЕРОВ ПЕРЕД НАСТРОЙКОЙ!**
        logger.info(f"🧹 Очищаем кэш парсеров перед настройкой...")
        if hasattr(selenium_parser, 'site_parsers'):
            old_cache_size = len(selenium_parser.site_parsers)
            selenium_parser.site_parsers.clear()  # ← ОЧИСТКА КЭША!
            logger.info(f"🧹 Удалено {old_cache_size} парсеров из кэша")

        # 🔥 **КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 3: ПРИНУДИТЕЛЬНО устанавливаем город**
        city = settings.city.strip() if settings.city else "Москва"

        # ЖЕСТКО устанавливаем город ДО вызова configure_for_user
        selenium_parser.current_city = city
        selenium_parser.current_user_id = request.user.id
        selenium_parser.current_user_username = request.user.username

        logger.info(f"🔥 ПРИНУДИТЕЛЬНО УСТАНОВЛЕНО:")
        logger.info(f"   - Город: '{selenium_parser.current_city}'")
        logger.info(f"   - User ID: {selenium_parser.current_user_id}")

        # Вызываем configure_for_user
        if hasattr(selenium_parser, 'configure_for_user'):
            success_config = selenium_parser.configure_for_user(
                user_id=request.user.id,
                username=request.user.username
            )
            logger.info(f"✅ configure_for_user вызван: {success_config}")

        logger.info(f"✅ Парсер настроен")
        logger.info(f"🏙️ ФИНАЛЬНЫЙ ГОРОД ПАРСЕРА: '{selenium_parser.current_city}'")

        # 🔥 **КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 3: Создаем объект настроек парсера**
        from apps.parsing.utils.parser_settings import ParserSettings as ParserDataclass

        try:
            # Преобразуем строку ключевых слов в список
            keywords_str = getattr(settings, 'keywords', '')
            if not keywords_str:
                logger.error(f"❌ В настройках нет ключевых слов!")
                return JsonResponse({
                    'status': 'error',
                    'message': 'В настройках не указаны ключевые слова для поиска'
                }, status=400)

            parser_settings_obj = ParserDataclass(
                keywords=keywords_str,
                exclude_keywords=getattr(settings, 'exclude_keywords', ''),
                min_price=float(getattr(settings, 'min_price', 0)),
                max_price=float(getattr(settings, 'max_price', 100000)),
                min_rating=float(getattr(settings, 'min_rating', 4.0)),
                seller_type=getattr(settings, 'seller_type', 'all'),
                browser_windows=int(getattr(settings, 'browser_windows', 1)),
                check_interval=int(getattr(settings, 'check_interval', 30)),
                max_items_per_hour=int(getattr(settings, 'max_items_per_hour', 10)),
                is_active=True
            )

            logger.info(f"📊 Создан объект настроек парсера")
            logger.info(f"   Ключевые слова: '{keywords_str}'")
            logger.info(f"   Список ключевых слов: {parser_settings_obj.get_keywords_list()}")

        except Exception as e:
            logger.error(f"❌ Ошибка создания объекта настроек: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка в настройках парсера: {str(e)}'
            }, status=500)

        # 🔥 **КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 4: Запускаем парсер в отдельном потоке**
        import threading
        import asyncio

        def run_parser_in_thread():
            """Запускает парсер в отдельном потоке"""
            try:
                # Создаем новую event loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                logger.info(f"🧵 Запуск парсера в отдельном потоке для {request.user.username}")
                logger.info(f"🏙️ Город для поиска: '{selenium_parser.current_city}'")
                logger.info(f"🌐 Сайт: {site}")

                # Запускаем парсер
                if asyncio.iscoroutinefunction(selenium_parser.start_with_settings):
                    logger.info(f"⚡ Используем асинхронный запуск")
                    loop.run_until_complete(
                        selenium_parser.start_with_settings(
                            settings=parser_settings_obj,
                            site=site
                        )
                    )
                else:
                    logger.info(f"🔄 Используем синхронный запуск")
                    selenium_parser.start_with_settings(
                        settings=parser_settings_obj,
                        site=site
                    )

                logger.info(f"✅ Парсер завершил работу для {request.user.username}")
                loop.close()

            except Exception as e:
                logger.error(f"❌ Ошибка в потоке парсера: {e}")
                import traceback
                logger.error(f"🔍 Детали ошибки в потоке: {traceback.format_exc()}")

        # Создаем и запускаем поток
        parser_thread = threading.Thread(
            target=run_parser_in_thread,
            name=f"ParserThread-{request.user.username}",
            daemon=True
        )
        parser_thread.start()

        logger.info(f"🚀 Парсер запущен в отдельном потоке для {request.user.username}")

        return JsonResponse({
            'status': 'success',
            'message': f'Парсер запущен для {request.user.username}',
            'user': {
                'id': request.user.id,
                'username': request.user.username
            },
            'settings': {
                'id': settings.id,
                'name': settings.name,
                'city': settings.city,
                'site': site
            },
            'parser_info': {
                'current_city': selenium_parser.current_city,
                'current_user_id': selenium_parser.current_user_id
            }
        })

    except ParserSettings.DoesNotExist:
        logger.error(f"❌ Настройки не найдены для пользователя {request.user.username}")
        return JsonResponse({
            'status': 'error',
            'message': 'Настройки не найдены или у вас нет доступа'
        }, status=404)

    except Exception as e:
        logger.error(f"❌ Ошибка запуска парсера: {e}")
        import traceback
        logger.error(f"🔍 Детали ошибки: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка запуска: {str(e)}'
        }, status=500)