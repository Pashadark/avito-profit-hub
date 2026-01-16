/**
 * Notifications System - обертки над Toastr с улучшенными анимациями
 */

(function($) {
    'use strict';

    // Проверяем наличие Toastr
    if (typeof toastr === 'undefined') {
        console.error('Toastr is not loaded! Please include toastr.js before notifications.js');
        return;
    }

    // Сохраняем оригинальные методы Toastr
    var originalToastrShow = toastr.success;
    var originalToastrError = toastr.error;
    var originalToastrInfo = toastr.info;
    var originalToastrWarning = toastr.warning;

    // Настройки Toastr (как в твоем скриншоте)
    toastr.options = {
        "closeButton": true,
        "debug": false,
        "newestOnTop": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "preventDuplicates": false,
        "onclick": null,
        "showDuration": "300",
        "hideDuration": "1000",
        "timeOut": "7500",
        "extendedTimeOut": "1000",
        "showEasing": "swing",
        "hideEasing": "linear",
        "showMethod": "fadeIn",
        "hideMethod": "fadeOut",
        "tapToDismiss": false,
        "closeOnHover": false, // ← ДОБАВЬТЕ ЭТУ СТРОЧКУ
        "target": "body"
    };

    // ============ УЛУЧШЕННЫЕ ФУНКЦИИ TOASTR ============

    // Обертка для всех toastr функций с улучшенной анимацией
    function enhancedToastr(type, message, title, options) {
        // Используем оригинальный toastr
        var $toast;
        switch(type) {
            case 'success':
                $toast = originalToastrShow.call(toastr, message, title, options);
                break;
            case 'error':
                $toast = originalToastrError.call(toastr, message, title, options);
                break;
            case 'info':
                $toast = originalToastrInfo.call(toastr, message, title, options);
                break;
            case 'warning':
                $toast = originalToastrWarning.call(toastr, message, title, options);
                break;
        }

        if ($toast && $toast.length) {
            // Добавляем плавную анимацию закрытия
            $toast.find('.toast-close-button').on('click', function(e) {
                e.stopPropagation();
                $toast.addClass('hiding');
                setTimeout(function() {
                    if ($toast.parent().length) {
                        $toast.remove();
                    }
                }, 400);
            });

            // Автоматическое закрытие с анимацией
            if (toastr.options.timeOut > 0) {
                setTimeout(function() {
                    if ($toast.length && $toast.is(':visible')) {
                        $toast.addClass('hiding');
                        setTimeout(function() {
                            if ($toast.parent().length) {
                                $toast.remove();
                            }
                        }, 400);
                    }
                }, toastr.options.timeOut);
            }
        }

        return $toast;
    }

    // Переопределяем методы Toastr
    toastr.success = function(message, title, options) {
        return enhancedToastr('success', message, title, options);
    };

    toastr.error = function(message, title, options) {
        return enhancedToastr('error', message, title, options);
    };

    toastr.info = function(message, title, options) {
        return enhancedToastr('info', message, title, options);
    };

    toastr.warning = function(message, title, options) {
        return enhancedToastr('warning', message, title, options);
    };

    // ============ НАШИ ФУНКЦИИ ============

    /**
     * Показывает успешное уведомление
     */
    window.notificationSuccess = function(message, title = 'Успешно') {
        console.log('🔔 notificationSuccess:', message, title);
        return toastr.success(message, title);
    };

    /**
     * Показывает уведомление об ошибке
     */
    window.notificationError = function(message, title = 'Ошибка') {
        console.log('🔔 notificationError:', message, title);
        return toastr.error(message, title);
    };

    /**
     * Показывает информационное уведомление
     */
    window.notificationInfo = function(message, title = 'Информация') {
        console.log('🔔 notificationInfo:', message, title);
        return toastr.info(message, title);
    };

    /**
     * Показывает предупреждение
     */
    window.notificationWarning = function(message, title = 'Внимание') {
        console.log('🔔 notificationWarning:', message, title);
        return toastr.warning(message, title);
    };

    /**
     * Основная функция для показа уведомлений
     */
    window.notificationAlert = function(message, type = 'info', title = '') {
        console.log('🔔 notificationAlert:', { message, type, title });

        if (!title) {
            const titles = {
                'success': 'Успешно',
                'error': 'Ошибка',
                'warning': 'Внимание',
                'info': 'Информация'
            };
            title = titles[type] || 'Уведомление';
        }

        switch(type.toLowerCase()) {
            case 'success':
                return toastr.success(message, title);
            case 'error':
            case 'danger':
                return toastr.error(message, title);
            case 'warning':
                return toastr.warning(message, title);
            case 'info':
            default:
                return toastr.info(message, title);
        }
    };

    /**
     * Важное уведомление с подсветкой
     */
    window.notificationImportant = function(message, title = 'Важно!') {
        const $toast = toastr.error(message, title, {
            timeOut: 8000,
            progressBar: true
        });

        if ($toast) {
            $toast.addClass('important');
            setTimeout(() => $toast.removeClass('important'), 2000);
        }

        return $toast;
    };

    /**
     * Уведомление с тряской (для ошибок)
     */
    window.notificationShake = function(message, title = 'Ошибка') {
        const $toast = toastr.error(message, title);

        if ($toast) {
            $toast.addClass('new');
            setTimeout(() => $toast.removeClass('new'), 500);
        }

        return $toast;
    };

    /**
     * Очищает все уведомления с анимацией
     */
    window.notificationClear = function() {
        $('.toast').each(function() {
            var $toast = $(this);
            $toast.addClass('hiding');
            setTimeout(function() {
                $toast.remove();
            }, 400);
        });
    };

    /**
     * Удаляет конкретное уведомление с анимацией
     */
    window.notificationRemove = function($notificationElement) {
        if ($notificationElement) {
            $notificationElement.addClass('hiding');
            setTimeout(function() {
                $notificationElement.remove();
            }, 400);
        }
    };

    // ============ СТАРЫЕ ФУНКЦИИ ДЛЯ СОВМЕСТИМОСТИ ============

    window.showToast = function(message, type = 'info', title = '') {
        window.notificationAlert(message, type, title);
    };

    window.showSuccess = function(message, title = 'Успешно') {
        window.notificationSuccess(message, title);
    };

    window.showError = function(message, title = 'Ошибка') {
        window.notificationError(message, title);
    };

    window.showInfo = function(message, title = 'Информация') {
        window.notificationInfo(message, title);
    };

    window.showWarning = function(message, title = 'Внимание') {
        window.notificationWarning(message, title);
    };

    // ============ ИНИЦИАЛИЗАЦИЯ ============

    $(document).ready(function() {
        console.log('✅ Notifications system initialized with enhanced animations');

        // Тестовое уведомление при загрузке
        setTimeout(function() {
            if (window.location.href.indexOf('debug') !== -1) {
                notificationSuccess('Система уведомлений готова!', 'Notifications');
            }
        }, 1000);
    });

})(jQuery);