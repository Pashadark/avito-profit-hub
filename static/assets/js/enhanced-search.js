// static/assets/js/enhanced-search.js
// JavaScript для расширенного поиска в шапке сайта

$(document).ready(function() {
    console.log('✅ Загружен enhanced-search.js');

    // 1. Сначала тестируем API
    testDirectAPI();

    // 2. Тест нажатия клавиш
    $(document).on('keydown', function(e) {
        console.log('⌨️ Клавиша нажата:', e.key, 'KeyCode:', e.keyCode, 'Ctrl:', e.ctrlKey, 'Shift:', e.shiftKey);

        // Ctrl + /
        if ((e.ctrlKey || e.metaKey) && (e.key === '/' || e.keyCode === 191)) {
            console.log('🔍 Ctrl+/ нажато! Фокус на поиск');
            e.preventDefault();

            const $searchWrapper = $('.search-input-wrapper');
            const $searchInput = $('.search-input');

            if ($searchWrapper.length === 0) {
                console.error('❌ Не найден .search-input-wrapper');
                return;
            }

            if ($searchInput.length === 0) {
                console.error('❌ Не найден .search-input');
                return;
            }

            // Переключаем видимость
            $searchWrapper.toggleClass('d-none');

            if (!$searchWrapper.hasClass('d-none')) {
                console.log('📝 Открываем поиск');
                $searchInput.focus();
                $searchInput.select();
            } else {
                console.log('❌ Закрываем поиск');
            }
        }

        // ESC - закрыть всё
        if (e.key === 'Escape') {
            console.log('⎋ ESC - закрываем поиск');
            $('.search-input-wrapper').addClass('d-none');
            $('.search-input').val('');
            hideSearchResults();
        }
    });

    // 3. Инициализация основного поиска
    initHeaderSearch();

    // 4. Добавляем кнопку тестирования
    addTestButton();
});

/**
 * Прямое тестирование API
 */
function testDirectAPI() {
    console.log('🔍 ПРЯМОЕ ТЕСТИРОВАНИЕ API...');

    // Список возможных URL для теста
    const testUrls = [
        '/api/search/header/?q=test',
        '/dashboard/api/search/header/?q=test',
        '/search/api/header/?q=test',
        '/header-search/?q=test'
    ];

    console.log('📋 Возможные URL API:', testUrls);

    // Тестируем каждый URL
    testUrls.forEach(url => {
        console.log(`📡 Тестируем ${url}...`);

        fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            console.log(`   ${url}:`);
            console.log(`     📊 Статус: ${response.status} ${response.statusText}`);
            console.log(`     🔗 URL ответа: ${response.url}`);
            console.log(`     ✅ OK: ${response.ok}`);

            if (response.ok) {
                return response.json().then(data => {
                    console.log(`     📦 Данные:`, data);
                    console.log(`     🎯 Товаров: ${data.pages?.length || 0}`);
                });
            } else {
                return response.text().then(text => {
                    console.log(`     ❌ Ошибка HTML:`, text.substring(0, 200));
                });
            }
        })
        .catch(error => {
            console.log(`     ❌ Ошибка запроса: ${error.message}`);
        });
    });
}

/**
 * Добавление кнопки тестирования
 */
function addTestButton() {
    // Удаляем старую кнопку если есть
    $('#test-search-btn').remove();

    // Добавляем новую кнопку
    $('body').append(`
        <div style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
            <button id="test-search-btn" class="btn btn-danger btn-sm shadow-lg">
                🔍 ТЕСТ ПОИСКА
            </button>
            <button id="test-api-btn" class="btn btn-warning btn-sm shadow-lg mt-1">
                📡 ТЕСТ API
            </button>
        </div>
    `);

    // Кнопка теста поиска
    $('#test-search-btn').on('click', function() {
        console.log('🔄 РУЧНОЙ ТЕСТ ПОИСКА...');

        // 1. Показываем поле поиска
        const $searchWrapper = $('.search-input-wrapper');
        const $searchInput = $('.search-input');

        $searchWrapper.removeClass('d-none');
        $searchInput.val('Mazda').focus();

        // 2. Ждем и запускаем поиск
        setTimeout(() => {
            console.log('🔄 Автоматический поиск "Mazda"...');
            performLiveSearch('Mazda');
        }, 500);

        // 3. Через 3 секунды показываем результат
        setTimeout(() => {
            console.log('📊 Проверяем результат...');
            const $results = $('.search-results-container');
            if ($results.length > 0 && $results.is(':visible')) {
                console.log('✅ Результаты поиска отображаются');
            } else {
                console.log('❌ Результаты поиска НЕ отображаются');
            }
        }, 3000);
    });

    // Кнопка теста API
    $('#test-api-btn').on('click', function() {
        console.log('📡 РУЧНОЙ ТЕСТ API...');

        // Тест нескольких запросов
        const queries = ['Mazda', 'Kia', 'Toyota', 'test', 'авто'];

        queries.forEach(query => {
            setTimeout(() => {
                console.log(`📡 Тест API с запросом: "${query}"`);

                $.ajax({
                    url: '/api/search/header/',
                    data: { q: query },
                    dataType: 'json',
                    timeout: 3000,
                    beforeSend: function(xhr) {
                        console.log(`   📤 Отправка: ${query}`);
                    },
                    success: function(data, status, xhr) {
                        console.log(`   ✅ Успех: ${query}`);
                        console.log(`      Код: ${xhr.status}`);
                        console.log(`      Товаров: ${data.pages?.length || 0}`);
                        console.log(`      Запросов: ${data.files?.length || 0}`);
                        console.log(`      Подсказок: ${data.suggestions?.length || 0}`);
                    },
                    error: function(xhr, status, error) {
                        console.log(`   ❌ Ошибка: ${query}`);
                        console.log(`      Статус: ${xhr.status}`);
                        console.log(`      Текст: ${xhr.statusText}`);
                        console.log(`      Ошибка: ${error}`);

                        // Пробуем другие URL
                        if (xhr.status === 404) {
                            console.log('   🔄 Пробуем альтернативные URL...');
                            testAlternativeUrls(query);
                        }
                    }
                });
            }, queries.indexOf(query) * 500);
        });
    });
}

/**
 * Тест альтернативных URL
 */
function testAlternativeUrls(query) {
    const altUrls = [
        '/dashboard/search/header/',
        '/search/header/',
        '/header-search/',
        '/api/header-search/'
    ];

    altUrls.forEach(url => {
        setTimeout(() => {
            $.ajax({
                url: url,
                data: { q: query },
                success: function(data) {
                    console.log(`   🎉 Найден рабочий URL: ${url}`);
                },
                error: function() {
                    console.log(`   ❌ Не работает: ${url}`);
                }
            });
        }, 100);
    });
}

/**
 * Инициализация поиска в шапке
 */
function initHeaderSearch() {
    console.log('🔍 ИНИЦИАЛИЗАЦИЯ ПОИСКА В ШАПКЕ...');

    const $searchWrapper = $('.search-input-wrapper');
    const $searchInput = $('.search-input');
    const $searchToggler = $('.search-toggler');

    console.log('📊 Найдены элементы:', {
        wrapper: $searchWrapper.length ? '✅' : '❌',
        input: $searchInput.length ? '✅' : '❌',
        toggler: $searchToggler.length ? '✅' : '❌'
    });

    if ($searchWrapper.length === 0) {
        console.error('❌ КРИТИЧЕСКАЯ ОШИБКА: Не найден .search-input-wrapper');
        console.error('   Проверьте HTML разметку');
        return;
    }

    if ($searchInput.length === 0) {
        console.error('❌ КРИТИЧЕСКАЯ ОШИБКА: Не найден .search-input');
        return;
    }

    // Открытие/закрытие поиска по клику на иконку
    $searchToggler.on('click', function(e) {
        e.preventDefault();
        console.log('🖱️ Клик по иконке поиска');

        $searchWrapper.toggleClass('d-none');

        if (!$searchWrapper.hasClass('d-none')) {
            console.log('📝 Открываем поле поиска');
            $searchInput.focus();
            $searchInput.select();
        } else {
            console.log('❌ Закрываем поле поиска');
            hideSearchResults();
        }
    });

    // Закрытие по клику на крестик
    $('.search-input-wrapper .ri-close-line').on('click', function(e) {
        e.stopPropagation();
        console.log('❌ Клик по крестику');
        $searchWrapper.addClass('d-none');
        hideSearchResults();
    });

    // Поиск при вводе
    let searchTimeout;
    $searchInput.on('input', function() {
        clearTimeout(searchTimeout);
        const query = $(this).val().trim();
        console.log('📝 Ввод в поиске:', query);

        if (query.length < 2) {
            hideSearchResults();
            return;
        }

        searchTimeout = setTimeout(() => {
            console.log('🔍 Выполняем поиск для:', query);
            performLiveSearch(query);
        }, 300);
    });

    // Enter - переход на страницу поиска
    $searchInput.on('keydown', function(e) {
        if (e.key === 'Enter' && $(this).val().trim()) {
            e.preventDefault();
            const query = $(this).val().trim();
            console.log('🚀 Переход на страницу поиска:', query);
            window.location.href = `/search/?q=${encodeURIComponent(query)}`;
        }
    });
}

/**
 * Быстрый поиск при вводе
 */
function performLiveSearch(query) {
    console.log('🔍 Поиск по базе:', query);

    // Показываем загрузку
    const $searchInput = $('.search-input');
    $searchInput.addClass('searching');

    // AJAX запрос
    $.ajax({
        url: '/api/search/header/',
        data: { q: query },
        dataType: 'json',
        timeout: 5000,
        success: function(data) {
            console.log('✅ Данные получены:', data);
            displayLiveSearchResults(data);
        },
        error: function(xhr) {
            console.error('❌ Ошибка AJAX:', xhr.status);

            // Показываем ошибку
            const $wrapper = $('.search-input-wrapper');
            let $results = $wrapper.find('.search-results-container');

            if ($results.length === 0) {
                $results = $('<div class="search-results-container"></div>');
                $wrapper.append($results);
            }

            $results.html(`
                <div class="search-no-results">
                    <i class="ri-error-warning-line ri-2x text-danger"></i>
                    <p class="mb-1">Ошибка при поиске</p>
                    <small class="text-muted">Статус: ${xhr.status}</small>
                </div>
            `).show();
        },
        complete: function() {
            $searchInput.removeClass('searching');
        }
    });
}

/**
 * Пробуем альтернативный поиск
 */
function tryAlternativeSearch(query) {
    const altUrls = [
        '/dashboard/api/search/header/',
        '/search/api/header/',
        '/api/header-search/'
    ];

    altUrls.forEach((url, index) => {
        setTimeout(() => {
            console.log(`🔄 Пробуем альтернативный URL ${index + 1}: ${url}`);

            $.ajax({
                url: url,
                data: { q: query },
                success: function(data) {
                    console.log(`🎉 Альтернативный URL работает: ${url}`);
                    displayLiveSearchResults(data);
                },
                error: function() {
                    console.log(`❌ Альтернативный URL не работает: ${url}`);
                }
            });
        }, index * 300);
    });
}

/**
 * Показать ошибку поиска
 */
function showSearchError(xhr, error) {
    const $wrapper = $('.search-input-wrapper');
    let $results = $wrapper.find('.search-results-container');

    if ($results.length === 0) {
        $results = $('<div class="search-results-container"></div>');
        $wrapper.append($results);
    }

    let errorMessage = 'Ошибка при поиске';
    if (xhr.status === 404) {
        errorMessage = 'API поиска не найден (404)';
    } else if (xhr.status === 403) {
        errorMessage = 'Доступ запрещен (CSRF ошибка)';
    } else if (xhr.status === 500) {
        errorMessage = 'Ошибка сервера';
    } else if (xhr.status === 0) {
        errorMessage = 'Нет связи с сервером';
    }

    $results.html(`
        <div class="search-no-results">
            <i class="ri-error-warning-line ri-3x mb-3 text-danger"></i>
            <p class="mb-1"><strong>${errorMessage}</strong></p>
            <p class="mb-1 small">Код: ${xhr.status} - ${xhr.statusText}</p>
            <small class="text-muted">${error || 'Попробуйте позже'}</small>
            <hr>
            <small class="text-muted">Проверьте консоль для подробностей</small>
        </div>
    `).show();
}

/**
 * Отображение результатов живого поиска
 */
function displayLiveSearchResults(data) {
    console.log('🎯 Отображаем результаты:', data.total_results, 'товаров');

    const $wrapper = $('.search-input-wrapper');
    let html = '';

    if (!data.pages || data.pages.length === 0) {
        html = `
            <div class="search-no-results">
                <i class="ri-search-line ri-3x mb-3"></i>
                <p class="mb-1">Ничего не найдено</p>
                <small class="text-muted">Попробуйте другой запрос</small>
                <div class="mt-3">
                    <small class="text-muted">Примеры:</small>
                    <div class="d-flex flex-wrap gap-1 mt-1">
                        <span class="badge bg-light text-dark" onclick="$('.search-input').val('авто').trigger('input')">авто</span>
                        <span class="badge bg-light text-dark" onclick="$('.search-input').val('москва').trigger('input')">москва</span>
                        <span class="badge bg-light text-dark" onclick="$('.search-input').val('2023').trigger('input')">2023</span>
                        <span class="badge bg-light text-dark" onclick="$('.search-input').val('черный').trigger('input')">черный</span>
                    </div>
                </div>
            </div>
        `;
    } else {
        // Заголовок
        html += `<div class="search-category">Найдено: ${data.total_results} товаров</div>`;

        // Товары
        data.pages.forEach((item, index) => {
            const photoHtml = item.photo ?
                `<img src="${item.photo}" alt="${item.name}" class="search-item-img">` :
                `<div class="search-item-icon"><i class="${item.icon || 'ri-car-line'}"></i></div>`;

            html += `
                <a href="${item.url}" class="search-result-item">
                    <div class="d-flex align-items-center">
                        <div class="search-item-img me-2">
                            ${photoHtml}
                        </div>
                        <div class="search-item-info flex-grow-1">
                            <h6 class="mb-1">${item.name}</h6>
                            <div class="search-item-meta small text-muted mb-1">
                                ${item.price} • ${item.category || ''} • ${item.location || ''}
                            </div>
                            ${item.profit ? `<span class="badge bg-success">${item.profit}</span>` : ''}
                        </div>
                    </div>
                </a>
            `;
        });

        // Подсказки
        if (data.suggestions && data.suggestions.length > 0) {
            html += `<div class="search-category mt-2">Подсказки</div>`;
            data.suggestions.forEach(suggestion => {
                html += `
                    <div class="search-suggestion" onclick="$('.search-input').val('${suggestion.split(' ')[0]}').trigger('input')">
                        <i class="ri-search-line me-2"></i>
                        <span>${suggestion}</span>
                    </div>
                `;
            });
        }
    }

    // Показываем результаты
    let $results = $wrapper.find('.search-results-container');
    if ($results.length === 0) {
        $results = $('<div class="search-results-container"></div>');
        $wrapper.append($results);
    }

    $results.html(html).show();
}
/**
 * Скрытие результатов поиска
 */
function hideSearchResults() {
    console.log('👻 Скрываем результаты поиска');
    $('.search-results-container').hide();
}

/**
 * Получение CSRF токена из cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Экспортируем функции
window.searchFunctions = {
    initHeaderSearch,
    performLiveSearch,
    displayLiveSearchResults,
    hideSearchResults,
    getCookie
};

console.log('🚀 enhanced-search.js полностью загружен и готов к работе!');
console.log('📋 Доступные функции:', Object.keys(window.searchFunctions));