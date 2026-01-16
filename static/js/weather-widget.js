// =============================================
// weather-ultimate-timeofday-enormous-clouds.js
// УЛЬТИМАТИВНЫЙ ПОГОДНЫЙ ВИДЖЕТ С ОГРОМНЫМИ ПУШИСТЫМИ ОБЛАКАМИ
// =============================================

(function() {
    console.log('☁️ СОЗДАЕМ ОГРОМНЫЕ ПУШИСТЫЕ ОБЛАКА...');

    // =============================================
    // КОНФИГУРАЦИЯ
    // =============================================
    const CONFIG = {
        API_KEY: '7d512c6fd54539914fc8115ef1acabe1',
        UPDATE_INTERVAL: 10 * 60 * 1000,
        RUSSIAN_CITIES: {
            'Moscow': 'Москва',
            'Saint Petersburg': 'Санкт-Петербург',
            'Novosibirsk': 'Новосибирск',
            'Yekaterinburg': 'Екатеринбург',
            'Kazan': 'Казань',
            'Nizhny Novgorod': 'Нижний Новгород'
        }
    };

    // =============================================
    // ФОНЫ ДЛЯ РАЗНЫХ ВРЕМЕН СУТОК
    // =============================================
    const TIME_OF_DAY_BACKGROUNDS = {
        'midnight': 'linear-gradient(135deg, #000000 0%, #0A0A0A 25%, #141414 66%, #282825 100%)',
        'dawn': 'linear-gradient(135deg, #0F2027 0%, #2C5364 25%, #FF9966 66%, #FFD89B 100%)',
        'morning': 'linear-gradient(135deg, #FFD89B 0%, #FF9966 25%, #4C9AFF 100%)',
        'day': 'linear-gradient(135deg, #1E90FF 0%, #4C9AFF 50%, #6495ED 100%)',
        'evening': 'linear-gradient(135deg, #FF7E5F 0%, #FEB47B 33%, #8A2BE2 66%, #4B0082 100%)',
        'night': 'linear-gradient(135deg, #0F2027 0%, #203A43 33%, #2C5364 66%, #282825 100%)'
    };

    const TIME_OF_DAY_TEXT = {
        'midnight': { icon: '🌙', text: 'Полночь' },
        'dawn': { icon: '🌅', text: 'Рассвет' },
        'morning': { icon: '☀️', text: 'Утро' },
        'day': { icon: '🌤️', text: 'День' },
        'evening': { icon: '🌆', text: 'Вечер' },
        'night': { icon: '🌃', text: 'Ночь' }
    };

    // =============================================
    // ВИДЫ ОГРОМНЫХ ПУШИСТЫХ ОБЛАКОВ
    // =============================================
    const CLOUD_TYPES = {
        ENORMOUS_FLUFFY: {
            name: 'Огромные пушистые',
            minSize: 300,      // УВЕЛИЧИЛ ДО 300
            maxSize: 600,      // УВЕЛИЧИЛ ДО 600
            blobCount: 15,     // УВЕЛИЧИЛ ДО 15
            blobSizeRange: { min: 50, max: 120 }, // УВЕЛИЧИЛ
            opacityRange: { min: 0.3, max: 0.7 },
            speedRange: { slow: 120, fast: 200 },
            colorVariation: 1.0,
            blur: 25,          // УВЕЛИЧИЛ РАЗМЫТИЕ
            isMassive: true
        },
        BIG_FLUFFY: {
            name: 'Большие пушистые',
            minSize: 200,      // УВЕЛИЧИЛ
            maxSize: 400,      // УВЕЛИЧИЛ
            blobCount: 10,     // УВЕЛИЧИЛ
            blobSizeRange: { min: 40, max: 90 },
            opacityRange: { min: 0.25, max: 0.6 },
            speedRange: { slow: 100, fast: 180 },
            colorVariation: 1.0,
            blur: 20
        },
        MEDIUM_SOFT: {
            name: 'Средние мягкие',
            minSize: 120,      // УВЕЛИЧИЛ
            maxSize: 280,      // УВЕЛИЧИЛ
            blobCount: 8,      // УВЕЛИЧИЛ
            blobSizeRange: { min: 30, max: 70 },
            opacityRange: { min: 0.2, max: 0.5 },
            speedRange: { slow: 80, fast: 150 },
            colorVariation: 0.9,
            blur: 15
        },
        SMALL_LIGHT: {
            name: 'Маленькие легкие',
            minSize: 80,       // УВЕЛИЧИЛ
            maxSize: 200,      // УВЕЛИЧИЛ
            blobCount: 6,      // УВЕЛИЧИЛ
            blobSizeRange: { min: 25, max: 60 },
            opacityRange: { min: 0.15, max: 0.4 },
            speedRange: { slow: 60, fast: 120 },
            colorVariation: 0.8,
            blur: 10
        },
        WISPY: {
            name: 'Перистые',
            minSize: 100,      // УВЕЛИЧИЛ
            maxSize: 250,      // УВЕЛИЧИЛ
            blobCount: 7,      // УВЕЛИЧИЛ
            blobSizeRange: { min: 20, max: 50 },
            opacityRange: { min: 0.1, max: 0.3 },
            speedRange: { slow: 150, fast: 250 }, // БЫСТРЕЕ ДЛЯ ПРОЛЕТА
            colorVariation: 0.7,
            blur: 8,
            isWispy: true
        }
    };

    // =============================================
    // АНИМАЦИИ ДЛЯ РАЗНЫХ ПОГОДНЫХ УСЛОВИЙ
    // =============================================
    const ANIMATIONS = {
        CLEAR_DAY: {
            elements: ['sun'],
            cloudTypes: [CLOUD_TYPES.WISPY, CLOUD_TYPES.SMALL_LIGHT],
            slowClouds: 2,     // УВЕЛИЧИЛ
            fastClouds: 5      // УВЕЛИЧИЛ
        },
        CLEAR_NIGHT: {
            elements: ['moon', 'stars'],
            cloudTypes: [CLOUD_TYPES.WISPY],
            slowClouds: 1,
            fastClouds: 4      // УВЕЛИЧИЛ
        },
        CLOUDS_DAY: {
            elements: ['sun'],
            cloudTypes: [CLOUD_TYPES.ENORMOUS_FLUFFY, CLOUD_TYPES.BIG_FLUFFY, CLOUD_TYPES.MEDIUM_SOFT],
            slowClouds: 6,     // УВЕЛИЧИЛ
            fastClouds: 12     // УВЕЛИЧИЛ
        },
        CLOUDS_NIGHT: {
            elements: ['moon', 'stars'],
            cloudTypes: [CLOUD_TYPES.BIG_FLUFFY, CLOUD_TYPES.MEDIUM_SOFT],
            slowClouds: 5,     // УВЕЛИЧИЛ
            fastClouds: 10     // УВЕЛИЧИЛ
        },
        RAIN_DAY: {
            elements: ['rain', 'clouds'],
            cloudTypes: [CLOUD_TYPES.ENORMOUS_FLUFFY],
            slowClouds: 8,     // УВЕЛИЧИЛ
            fastClouds: 15     // УВЕЛИЧИЛ
        },
        RAIN_NIGHT: {
            elements: ['rain', 'clouds', 'moon'],
            cloudTypes: [CLOUD_TYPES.ENORMOUS_FLUFFY, CLOUD_TYPES.BIG_FLUFFY],
            slowClouds: 7,     // УВЕЛИЧИЛ
            fastClouds: 13     // УВЕЛИЧИЛ
        },
        SNOW_DAY: {
            elements: ['snow', 'clouds'],
            cloudTypes: [CLOUD_TYPES.ENORMOUS_FLUFFY, CLOUD_TYPES.BIG_FLUFFY],
            slowClouds: 7,     // УВЕЛИЧИЛ
            fastClouds: 14     // УВЕЛИЧИЛ
        },
        SNOW_NIGHT: {
            elements: ['snow', 'clouds', 'moon'],
            cloudTypes: [CLOUD_TYPES.ENORMOUS_FLUFFY, CLOUD_TYPES.BIG_FLUFFY],
            slowClouds: 6,     // УВЕЛИЧИЛ
            fastClouds: 12     // УВЕЛИЧИЛ
        },
        THUNDERSTORM: {
            elements: ['lightning', 'rain', 'clouds'],
            cloudTypes: [CLOUD_TYPES.ENORMOUS_FLUFFY],
            slowClouds: 10,    // УВЕЛИЧИЛ
            fastClouds: 18     // УВЕЛИЧИЛ
        },
        FOG: {
            elements: ['fog'],
            cloudTypes: [CLOUD_TYPES.WISPY],
            slowClouds: 4,     // УВЕЛИЧИЛ
            fastClouds: 8      // УВЕЛИЧИЛ
        }
    };

    // =============================================
    // ОСНОВНЫЕ ФУНКЦИИ
    // =============================================

    // 1. Добавление стилей
    addStyles();

    // 2. Ожидание DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 100);
    }

    // =============================================
    // ИНИЦИАЛИЗАЦИЯ
    // =============================================
    async function init() {
        console.log('🎯 Инициализация с ОГРОМНЫМИ облаками...');

        const elements = getElements();
        if (!elements.temp) return;

        showLoading(elements);
        applyTimeOfDayBackground();

        try {
            const userCity = await getUserCity();
            await updateWeather(userCity || 'Moscow', elements);

            setInterval(() => updateWeather(userCity || 'Moscow', elements), CONFIG.UPDATE_INTERVAL);
            setInterval(() => applyTimeOfDayBackground(), 60 * 1000);

            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    applyTimeOfDayBackground();
                }
            });

        } catch (error) {
            console.error('Ошибка инициализации:', error);
            showDemoWeather('Moscow', elements);
        }
    }

    // =============================================
    // ФУНКЦИИ ДЛЯ ФОНА ВРЕМЕНИ СУТОК
    // =============================================
    function getTimeOfDay() {
        const now = new Date();
        const hour = now.getHours();
        const minute = now.getMinutes();
        const decimalHour = hour + (minute / 60);

        if (decimalHour >= 22 || decimalHour < 4) return 'midnight';
        else if (decimalHour >= 4 && decimalHour < 6) return 'dawn';
        else if (decimalHour >= 6 && decimalHour < 10) return 'morning';
        else if (decimalHour >= 10 && decimalHour < 16) return 'day';
        else if (decimalHour >= 16 && decimalHour < 19) return 'evening';
        else return 'night';
    }

    function applyTimeOfDayBackground() {
        const timeOfDay = getTimeOfDay();
        const background = TIME_OF_DAY_BACKGROUNDS[timeOfDay];

        const welcomeCard = document.getElementById('welcome-card');
        if (welcomeCard) {
            welcomeCard.style.background = '';
            setTimeOfDayClass(welcomeCard, timeOfDay);
            welcomeCard.style.background = background;
            updateTimeDisplay();
        }

        const weatherBg = document.getElementById('weather-bg');
        if (weatherBg) {
            weatherBg.style.background = '';
            setTimeOfDayClass(weatherBg, timeOfDay);
            weatherBg.style.background = background;
        }

        return timeOfDay;
    }

    function setTimeOfDayClass(element, timeOfDay) {
        const timeClasses = ['midnight', 'dawn', 'morning', 'day', 'evening', 'night'];
        timeClasses.forEach(cls => element.classList.remove(`${cls}-bg`));
        element.classList.add(`${timeOfDay}-bg`);
    }

    // =============================================
    // ФУНКЦИИ ПОГОДНОГО ВИДЖЕТА
    // =============================================
    function getElements() {
        return {
            temp: document.getElementById('weather-temp'),
            desc: document.getElementById('weather-desc'),
            city: document.getElementById('weather-location'),
            icon: document.getElementById('weather-icon'),
            bg: document.getElementById('weather-bg'),
            anim: document.getElementById('weather-animation'),
            time: document.getElementById('time-of-day')
        };
    }

    function showLoading(elements) {
        if (elements.temp) elements.temp.textContent = '...';
        if (elements.desc) elements.desc.textContent = '🌀 Обновляем...';
        if (elements.city) elements.city.textContent = '...';
        if (elements.icon) elements.icon.innerHTML = '🌀';
        updateTimeDisplay();
    }

    function updateTimeDisplay() {
        const timeOfDay = getTimeOfDay();
        const timeInfo = TIME_OF_DAY_TEXT[timeOfDay] || { icon: '🕒', text: timeOfDay };
        const timeIcon = document.getElementById('time-of-day-icon');
        const timeText = document.getElementById('time-of-day-text');
        const currentTime = document.getElementById('current-time');

        if (timeIcon) timeIcon.textContent = timeInfo.icon;
        if (timeText) timeText.textContent = timeInfo.text;
        if (currentTime) {
            currentTime.textContent = new Date().toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    async function getUserCity() {
        try {
            const response = await fetch('https://get.geojs.io/v1/ip/geo.json');
            const data = await response.json();
            return data.city || null;
        } catch {
            return null;
        }
    }

    async function updateWeather(city, elements) {
        try {
            const response = await fetch(
                `https://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${CONFIG.API_KEY}&units=metric&lang=ru`
            );
            const data = await response.json();
            if (data.cod === 200) {
                showRealWeather(data, elements);
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Ошибка API погоды:', error);
            showDemoWeather(city, elements);
        }
    }

    function showRealWeather(data, elements) {
        const temp = Math.round(data.main.temp);
        const feelsLike = Math.round(data.main.feels_like);
        const description = data.weather[0].description;
        const weatherId = data.weather[0].id;
        const cityName = CONFIG.RUSSIAN_CITIES[data.name] || data.name;

        if (elements.temp) elements.temp.textContent = `${temp > 0 ? '+' : ''}${temp}°C`;
        if (elements.desc) elements.desc.textContent = description.charAt(0).toUpperCase() + description.slice(1);
        if (elements.city) {
            elements.city.textContent = cityName;
            elements.city.title = `Ощущается как ${feelsLike > 0 ? '+' : ''}${feelsLike}°C`;
        }

        updateTimeDisplay();

        if (elements.icon) {
            elements.icon.innerHTML = getWeatherIcon(weatherId);
            elements.icon.title = `Влажность: ${data.main.humidity}%, Давление: ${data.main.pressure} hPa`;
        }

        const hour = new Date().getHours();
        const isDay = hour >= 6 && hour < 20;

        let animationKey = 'CLOUDS_DAY';
        if (weatherId >= 200 && weatherId < 300) animationKey = 'THUNDERSTORM';
        else if (weatherId >= 300 && weatherId < 600) animationKey = isDay ? 'RAIN_DAY' : 'RAIN_NIGHT';
        else if (weatherId >= 600 && weatherId < 700) animationKey = isDay ? 'SNOW_DAY' : 'SNOW_NIGHT';
        else if (weatherId === 800) animationKey = isDay ? 'CLEAR_DAY' : 'CLEAR_NIGHT';
        else if (weatherId > 800) animationKey = isDay ? 'CLOUDS_DAY' : 'CLOUDS_NIGHT';
        else if (weatherId >= 700 && weatherId < 800) animationKey = 'FOG';

        applyAnimation(animationKey, elements, isDay);
    }

    function showDemoWeather(city, elements) {
        const temp = Math.floor(Math.random() * 15) - 5;
        const cityName = CONFIG.RUSSIAN_CITIES[city] || city;

        if (elements.temp) elements.temp.textContent = `${temp > 0 ? '+' : ''}${temp}°C`;
        if (elements.desc) elements.desc.textContent = 'солнечно';
        if (elements.city) elements.city.textContent = cityName;
        if (elements.icon) {
            elements.icon.innerHTML = '☀️';
            elements.icon.title = 'Демо-данные';
        }

        const hour = new Date().getHours();
        const isDay = hour >= 6 && hour < 20;
        createDemoAnimation(isDay, elements);
    }

    function getWeatherIcon(weatherId) {
        if (weatherId >= 200 && weatherId < 210) return '⛈️';
        if (weatherId >= 210 && weatherId < 300) return '🌩️';
        if (weatherId >= 300 && weatherId < 400) return '🌦️';
        if (weatherId >= 500 && weatherId < 600) return '🌧️';
        if (weatherId >= 600 && weatherId < 700) return '❄️';
        if (weatherId === 701) return '🌫️';
        if (weatherId === 711) return '💨';
        if (weatherId === 721) return '🌁';
        if (weatherId === 731) return '🌪️';
        if (weatherId === 741) return '🌫️';
        if (weatherId === 751) return '🏜️';
        if (weatherId === 761) return '🌫️';
        if (weatherId === 762) return '🌋';
        if (weatherId === 771) return '💨';
        if (weatherId === 781) return '🌪️';
        if (weatherId === 800) return '☀️';
        if (weatherId === 801) return '🌤️';
        if (weatherId === 802) return '⛅';
        if (weatherId === 803) return '🌥️';
        if (weatherId === 804) return '☁️';
        return '🌈';
    }

    // =============================================
    // ФУНКЦИИ СОЗДАНИЯ ОГРОМНЫХ ПУШИСТЫХ ОБЛАКОВ
    // =============================================
    function createGiantFluffyCloud(cloudType, movementType, index, isDay) {
        const cloud = document.createElement('div');
        cloud.className = `fluffy-cloud ${movementType}-cloud cloud-${index} ${cloudType.isMassive ? 'massive-cloud' : ''}`;

        // РАЗМЕРЫ ОГРОМНЫХ ОБЛАКОВ
        const cloudWidth = cloudType.minSize + Math.random() * (cloudType.maxSize - cloudType.minSize);
        const cloudHeight = cloudWidth * (0.25 + Math.random() * 0.25); // Меньше высота для растянутости

        // ПОЗИЦИИ - ОБЛАКА ДОЛЖНЫ БЫТЬ НИЖЕ И БОЛЬШЕ
        const top = movementType === 'slow'
            ? (20 + Math.random() * 50)  // НИЖЕ
            : (10 + Math.random() * 60);

        // ДЛЯ ПРОЛЕТАЮЩИХ - НАЧИНАЕМ ЗА ЭКРАНОМ СЛЕВА
        const startLeft = movementType === 'slow'
            ? Math.random() * 100
            : -(cloudWidth + Math.random() * 400); // ЕЩЕ ДАЛЬШЕ

        // ЦВЕТ В ЗАВИСИМОСТИ ОТ ВРЕМЕНИ СУТОК
        let baseColor;
        let lightColor;

        if (isDay) {
            // ДНЕВНЫЕ ЦВЕТА - БЕЛЕЕ
            if (cloudType.isWispy) {
                baseColor = '255, 255, 255';
                lightColor = '255, 255, 255';
            } else {
                const brightness = 245 + Math.floor(Math.random() * 10);
                const blue = brightness;
                const red = brightness - Math.floor(Math.random() * 15 * cloudType.colorVariation);
                const green = brightness - Math.floor(Math.random() * 5 * cloudType.colorVariation);
                baseColor = `${red}, ${green}, ${blue}`;
                lightColor = '255, 255, 255';
            }
        } else {
            // НОЧНЫЕ ЦВЕТА - СИНЕВАТЫЕ
            if (cloudType.isWispy) {
                baseColor = '220, 230, 250';
                lightColor = '240, 245, 255';
            } else {
                const blue = 240 + Math.floor(Math.random() * 15);
                const red = 210 + Math.floor(Math.random() * 30 * cloudType.colorVariation);
                const green = 220 + Math.floor(Math.random() * 20 * cloudType.colorVariation);
                baseColor = `${red}, ${green}, ${blue}`;
                lightColor = `${red + 40}, ${green + 40}, ${blue + 40}`;
            }
        }

        // ПРОЗРАЧНОСТЬ - БОЛЬШЕ ДЛЯ ОГРОМНЫХ ОБЛАКОВ
        const opacity = cloudType.opacityRange.min +
            Math.random() * (cloudType.opacityRange.max - cloudType.opacityRange.min);

        // СОЗДАЕМ МНОЖЕСТВО BLOB'ОВ ДЛЯ ПУШИСТОСТИ
        let cloudHTML = '';
        const blobs = [];

        // ОСНОВНЫЕ BLOB'Ы
        for (let i = 0; i < cloudType.blobCount; i++) {
            const blobSize = cloudType.blobSizeRange.min +
                Math.random() * (cloudType.blobSizeRange.max - cloudType.blobSizeRange.min);

            // ПОЗИЦИИ ВНУТРИ ОБЛАКА - СКОНЦЕНТРИРОВАНЫ В ЦЕНТРЕ
            const centerX = cloudWidth * 0.5;
            const centerY = cloudHeight * 0.5;
            const blobX = centerX + (Math.random() - 0.5) * (cloudWidth * 0.8) - blobSize / 2;
            const blobY = centerY + (Math.random() - 0.5) * (cloudHeight * 0.6) - blobSize / 2;

            // ДЛЯ ПЕРИСТЫХ ОБЛАКОВ ДЕЛАЕМ БОЛЕЕ ВЫТЯНУТЫЕ BLOB'Ы
            const isElongated = cloudType.isWispy && Math.random() > 0.5;
            // ДЛЯ ОГРОМНЫХ ОБЛАКОВ - РАЗНЫЕ ФОРМЫ
            const shapeVariation = cloudType.isMassive ? Math.random() : 0.5;
            const isFlattened = shapeVariation > 0.7;

            blobs.push({
                x: blobX,
                y: blobY,
                size: blobSize,
                opacity: opacity * (0.7 + Math.random() * 0.5),
                elongated: isElongated,
                flattened: isFlattened,
                depth: Math.random() // Для z-index внутри облака
            });
        }

        // СОРТИРУЕМ ПО ГЛУБИНЕ ДЛЯ ОБЪЕМНОСТИ
        blobs.sort((a, b) => a.depth - b.depth);

        // РЕНДЕРИМ BLOB'Ы
        blobs.forEach((blob, i) => {
            const blobOpacity = blob.opacity * (0.9 + Math.random() * 0.2);
            const zIndex = Math.floor(blob.depth * 10);

            // ДЛЯ ПЛОСКИХ BLOB'ОВ - ДЕЛАЕМ ОВАЛЬНЫМИ
            const borderRadius = blob.flattened ? '40%' : (blob.elongated ? '30%' : '50%');
            const blobHeight = blob.flattened ?
                blob.size * (0.4 + Math.random() * 0.3) :
                (blob.elongated ? blob.size * 0.5 : blob.size);

            cloudHTML += `
                <div class="cloud-blob" style="
                    width: ${blob.size}px;
                    height: ${blobHeight}px;
                    left: ${blob.x}px;
                    top: ${blob.y}px;
                    background: rgba(${baseColor}, ${blobOpacity});
                    --blob-blur: ${cloudType.blur * (0.6 + Math.random() * 0.8)}px;
                    --blob-opacity: ${blobOpacity};
                    border-radius: ${borderRadius};
                    z-index: ${zIndex};
                    transform: rotate(${Math.random() * 10 - 5}deg);
                "></div>
            `;
        });

        // ДОБАВЛЯЕМ СВЕТОВЫЕ БЛИКИ (БОЛЬШЕ ДЛЯ ОГРОМНЫХ ОБЛАКОВ)
        const highlightCount = Math.floor(cloudType.blobCount * 0.4);
        for (let i = 0; i < highlightCount; i++) {
            const highlightX = Math.random() * cloudWidth;
            const highlightY = Math.random() * cloudHeight;
            const highlightSize = 30 + Math.random() * 60; // БОЛЬШЕ БЛИКИ

            cloudHTML += `
                <div class="cloud-light" style="
                    width: ${highlightSize}px;
                    height: ${highlightSize}px;
                    left: ${highlightX}px;
                    top: ${highlightY}px;
                    opacity: ${0.2 + Math.random() * 0.3};
                "></div>
            `;
        }

        // ДОБАВЛЯЕМ ВНУТРЕННЮЮ ТЕНЬ ДЛЯ ОБЪЕМА
        cloudHTML += `
            <div class="cloud-shadow" style="
                position: absolute;
                width: ${cloudWidth * 0.8}px;
                height: ${cloudHeight * 0.6}px;
                left: ${cloudWidth * 0.1}px;
                top: ${cloudHeight * 0.2}px;
                background: radial-gradient(
                    ellipse at center,
                    transparent 0%,
                    rgba(0, 0, 0, 0.05) 50%,
                    transparent 100%
                );
                filter: blur(${cloudType.blur * 0.5}px);
                opacity: 0.1;
                z-index: -1;
            "></div>
        `;

        cloud.innerHTML = cloudHTML;

        // АНИМАЦИИ - БОЛЬШИЕ ОБЛАКА ДВИГАЮТСЯ МЕДЛЕННЕЕ
        const animationDuration = movementType === 'slow'
            ? `${cloudType.speedRange.slow + Math.random() * 60}s` // МЕДЛЕННЕЕ
            : `${(cloudType.speedRange.fast + Math.random() * 50) / (cloudType.isMassive ? 2 : 1.5)}s`;

        const animationName = movementType === 'slow' ? 'floatGently' : 'flyMassiveAcross';

        // НАСТРАИВАЕМ ПЕРЕМЕННЫЕ CSS ДЛЯ АНИМАЦИИ
        const floatX = Math.random() * 50 - 25; // БОЛЬШЕ ДВИЖЕНИЯ
        const floatY = Math.random() * 40 - 20;
        const rotateStart = Math.random() * 8 - 4;
        const driftY = Math.random() * 150 - 75; // БОЛЬШЕ СНОСА

        cloud.style.cssText = `
            top: ${top}%;
            left: ${startLeft}%;
            width: ${cloudWidth}px;
            height: ${cloudHeight}px;
            --float-x: ${floatX};
            --float-y: ${floatY};
            --rotate-start: ${rotateStart};
            --drift-y: ${driftY};
            --start-x: ${startLeft};
            --opacity-start: ${opacity * 0.9};
            --opacity-mid: ${opacity};
            --opacity-peak: ${opacity * 1.1};
            --cloud-blur: ${cloudType.blur}px;
            animation:
                ${animationName} ${animationDuration} infinite ${movementType === 'slow' ? 'ease-in-out' : 'linear'},
                cloudAppear 3s ease-out ${index * 0.2}s both,
                colorPulse ${cloudType.speedRange.slow * 3}s infinite alternate ease-in-out;
            animation-delay: ${Math.random() * 20}s;
            z-index: ${movementType === 'slow' ? 2 : 1};
            transform-origin: center center;
        `;

        return cloud;
    }

    // =============================================
    // СОЗДАНИЕ ДЫМКИ
    // =============================================
    function createHazeLayer() {
        const haze = document.createElement('div');
        haze.className = 'haze-layer';
        return haze;
    }

    // =============================================
    // СОЗДАНИЕ ОБЛАЧНОГО НЕБА С ОГРОМНЫМИ ОБЛАКАМИ
    // =============================================
    function createGiantCloudSky(weatherCondition, isDay, container) {
        if (!container) return;

        // ОЧИЩАЕМ КОНТЕЙНЕР
        container.innerHTML = '';

        // ДОБАВЛЯЕМ ДЫМКУ
        container.appendChild(createHazeLayer());

        // ОПРЕДЕЛЯЕМ ТИПЫ ОБЛАКОВ ПО ПОГОДЕ
        let cloudTypes = [];
        let slowCount, fastCount;

        switch(weatherCondition) {
            case 'CLEAR_DAY':
                cloudTypes = [CLOUD_TYPES.WISPY, CLOUD_TYPES.SMALL_LIGHT];
                slowCount = 3;      // БОЛЬШЕ ОБЛАКОВ
                fastCount = 8;      // БОЛЬШЕ ПРОЛЕТАЮЩИХ
                break;
            case 'CLEAR_NIGHT':
                cloudTypes = [CLOUD_TYPES.WISPY];
                slowCount = 2;
                fastCount = 6;
                break;
            case 'CLOUDS_DAY':
                cloudTypes = [CLOUD_TYPES.ENORMOUS_FLUFFY, CLOUD_TYPES.BIG_FLUFFY, CLOUD_TYPES.MEDIUM_SOFT];
                slowCount = 8;      // ОЧЕНЬ МНОГО ОБЛАКОВ
                fastCount = 16;     // ОЧЕНЬ МНОГО ПРОЛЕТАЮЩИХ
                break;
            case 'CLOUDS_NIGHT':
                cloudTypes = [CLOUD_TYPES.BIG_FLUFFY, CLOUD_TYPES.MEDIUM_SOFT];
                slowCount = 6;
                fastCount = 14;
                break;
            case 'RAIN_DAY':
            case 'RAIN_NIGHT':
                cloudTypes = [CLOUD_TYPES.ENORMOUS_FLUFFY];
                slowCount = 10;
                fastCount = 20;     // ОЧЕНЬ МНОГО ГРОЗОВЫХ ОБЛАКОВ
                break;
            case 'SNOW_DAY':
            case 'SNOW_NIGHT':
                cloudTypes = [CLOUD_TYPES.ENORMOUS_FLUFFY, CLOUD_TYPES.BIG_FLUFFY];
                slowCount = 9;
                fastCount = 18;
                break;
            case 'THUNDERSTORM':
                cloudTypes = [CLOUD_TYPES.ENORMOUS_FLUFFY];
                slowCount = 12;
                fastCount = 24;     // МАКСИМАЛЬНО ОБЛАКОВ
                break;
            case 'FOG':
                cloudTypes = [CLOUD_TYPES.WISPY];
                slowCount = 5;
                fastCount = 12;
                break;
            default:
                cloudTypes = [CLOUD_TYPES.MEDIUM_SOFT];
                slowCount = 4;
                fastCount = 10;
        }

        console.log(`☁️🌪️ СОЗДАЕМ ${slowCount} МЕДЛЕННЫХ И ${fastCount} БЫСТРЫХ ОГРОМНЫХ ОБЛАКОВ!`);

        // СОЗДАЕМ МЕДЛЕННЫЕ ОБЛАКА
        for (let i = 0; i < slowCount; i++) {
            const cloudType = cloudTypes[Math.floor(Math.random() * cloudTypes.length)];
            const cloud = createGiantFluffyCloud(cloudType, 'slow', i, isDay);
            container.appendChild(cloud);
        }

        // СОЗДАЕМ БЫСТРЫЕ ПРОЛЕТАЮЩИЕ ОБЛАКА
        for (let i = 0; i < fastCount; i++) {
            const cloudType = cloudTypes[Math.floor(Math.random() * cloudTypes.length)];
            const cloud = createGiantFluffyCloud(cloudType, 'fast', i + slowCount, isDay);
            container.appendChild(cloud);
        }
    }

    // =============================================
    // ОСНОВНЫЕ АНИМАЦИОННЫЕ ФУНКЦИИ
    // =============================================
    function applyAnimation(animationKey, elements, isDay) {
        if (!elements.anim || !elements.time) return;

        const animation = ANIMATIONS[animationKey];
        if (!animation) return;

        clearAllAnimations(elements);
        createGiantCloudSky(animationKey, isDay, elements.anim);

        if (animation.elements) {
            animation.elements.forEach(elementType => {
                if (elementType !== 'clouds') {
                    createAnimationElement(elementType, elements, isDay);
                }
            });
        }

        console.log(`✅ Анимация "${animationKey}" создана с ОГРОМНЫМИ облаками!`);
    }

    function createDemoAnimation(isDay, elements) {
        const animationKey = isDay ? 'CLOUDS_DAY' : 'CLOUDS_NIGHT';
        applyAnimation(animationKey, elements, isDay);
    }

    function clearAllAnimations(elements) {
        if (elements.anim) elements.anim.innerHTML = '';
        if (elements.time) elements.time.innerHTML = '';
    }

    function createAnimationElement(type, elements, isDay) {
        const container = (type === 'sun' || type === 'moon' || type === 'clouds')
            ? elements.anim
            : elements.time;
        if (!container) return;

        switch(type) {
            case 'sun':
                createSun(container, isDay);
                break;
            case 'moon':
                createMoon(container, isDay);
                break;
            case 'stars':
                createStars(container, isDay);
                break;
            case 'rain':
                createRain(container, isDay);
                break;
            case 'snow':
                createSnow(container, isDay);
                break;
            case 'lightning':
                createLightning(container, isDay);
                break;
            case 'fog':
                createFog(container, isDay);
                break;
        }
    }

    // =============================================
    // ФУНКЦИИ СОЗДАНИЯ ДОПОЛНИТЕЛЬНЫХ ЭЛЕМЕНТОВ
    // =============================================
    function createSun(container, isDay) {
        const sun = document.createElement('div');
        sun.className = 'sun-animation';
        const size = 80; // БОЛЬШЕ СОЛНЦЕ

        sun.style.cssText = `
            position: absolute;
            top: 20px;
            right: 20px;
            width: ${size}px;
            height: ${size}px;
            background: #FFD700;
            border-radius: 50%;
            box-shadow: 0 0 60px rgba(255, 215, 0, 0.9), 0 0 120px rgba(255, 215, 0, 0.6);
            z-index: 10;
        `;
        container.appendChild(sun);
    }

    function createMoon(container, isDay) {
        const moon = document.createElement('div');
        moon.className = 'moon-animation';
        const size = 70; // БОЛЬШЕ ЛУНА

        moon.style.cssText = `
            position: absolute;
            top: 20px;
            right: 20px;
            width: ${size}px;
            height: ${size}px;
            background: #F5F5F5;
            border-radius: 50%;
            box-shadow: 0 0 40px rgba(245, 245, 245, 0.8),
                        inset -15px -8px 0 0 rgba(200, 200, 200, 0.4);
            z-index: 10;
        `;
        container.appendChild(moon);
    }

    function createStars(container, isDay) {
        const starCount = 50; // БОЛЬШЕ ЗВЕЗД

        for (let i = 0; i < starCount; i++) {
            const star = document.createElement('div');
            star.className = 'star';
            const size = Math.random() * 4 + 1; // БОЛЬШЕ ЗВЕЗДЫ
            const duration = Math.random() * 4 + 1;

            star.style.cssText = `
                position: absolute;
                background: white;
                border-radius: 50%;
                width: ${size}px;
                height: ${size}px;
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                animation: starTwinkle ${duration}s infinite alternate;
                animation-delay: ${Math.random() * 5}s;
                z-index: 5;
                box-shadow: 0 0 ${size * 3}px white;
                filter: blur(${size * 0.3}px);
            `;
            container.appendChild(star);
        }
    }

    function createRain(container, isDay) {
        const dropCount = 80; // БОЛЬШЕ ДОЖДЯ

        for (let i = 0; i < dropCount; i++) {
            const drop = document.createElement('div');
            drop.className = 'raindrop';
            const left = Math.random() * 100;
            const delay = Math.random() * 2;
            const duration = 0.6 + Math.random() * 0.8; // БЫСТРЕЕ
            const length = 20 + Math.random() * 20; // ДЛИННЕЕ

            drop.style.cssText = `
                position: absolute;
                background: ${isDay ? 'rgba(173, 216, 230, 0.8)' : 'rgba(135, 206, 250, 0.9)'};
                width: ${Math.random() * 2 + 0.8}px;
                height: ${length}px;
                left: ${left}%;
                top: -40px;
                border-radius: 2px;
                animation: rainFall ${duration}s linear infinite;
                animation-delay: ${delay}s;
                opacity: ${0.5 + Math.random() * 0.5};
                z-index: 15;
                filter: blur(0.5px);
            `;
            container.appendChild(drop);
        }
    }

    function createSnow(container, isDay) {
        const flakeCount = 120; // БОЛЬШЕ СНЕГА

        for (let i = 0; i < flakeCount; i++) {
            const flake = document.createElement('div');
            flake.className = 'snowflake';
            const size = Math.random() * 6 + 2; // БОЛЬШЕ СНЕЖИНКИ
            const left = Math.random() * 100;
            const delay = Math.random() * 5;
            const duration = 10 + Math.random() * 10; // МЕДЛЕННЕЕ
            const sway = 20 + Math.random() * 30; // БОЛЬШЕ СНОС

            flake.style.cssText = `
                position: absolute;
                background: white;
                border-radius: 50%;
                width: ${size}px;
                height: ${size}px;
                left: ${left}%;
                top: -20px;
                animation: snowFall ${duration}s linear infinite,
                          snowSway ${sway / 10}s ease-in-out infinite alternate;
                animation-delay: ${delay}s;
                opacity: ${0.7 + Math.random() * 0.3};
                filter: blur(${Math.random() * 1.2}px);
                z-index: 15;
                box-shadow: 0 0 ${size * 1.5}px white;
            `;
            container.appendChild(flake);
        }
    }

    function createLightning(container, isDay) {
        // СОЗДАЕМ НЕСКОЛЬКО МОЛНИЙ
        for (let i = 0; i < 3; i++) {
            const flash = document.createElement('div');
            flash.className = 'lightning-flash';
            const delay = i * 3;

            flash.style.cssText = `
                position: absolute;
                top: 0;
                left: ${20 + Math.random() * 60}%;
                width: 40%;
                height: 100%;
                background: linear-gradient(
                    to right,
                    transparent,
                    rgba(255, 255, 255, 0.4),
                    transparent
                );
                z-index: 20;
                animation: lightningFlash 0.1s ${delay}s infinite;
                opacity: 0;
                filter: blur(10px);
            `;
            container.appendChild(flash);
        }
    }

    function createFog(container, isDay) {
        for (let i = 0; i < 5; i++) { // БОЛЬШЕ ТУМАНА
            const fog = document.createElement('div');
            fog.className = 'fog-layer';
            const speed = 100 + i * 40;
            const height = 30 + Math.random() * 40;

            fog.style.cssText = `
                position: absolute;
                top: ${10 + i * 15}%;
                left: 0;
                width: 250%;
                height: ${height}%;
                background: linear-gradient(90deg,
                    transparent,
                    rgba(255,255,255,0.12),
                    rgba(255,255,255,0.2),
                    rgba(255,255,255,0.12),
                    transparent);
                animation: fogMove ${speed}s linear infinite;
                animation-delay: ${i * 10}s;
                filter: blur(${20 + i * 10}px);
                opacity: ${0.2 + i * 0.05};
                z-index: 25;
            `;
            container.appendChild(fog);
        }
    }

    // =============================================
    // ДОБАВЛЕНИЕ СТИЛЕЙ С ОГРОМНЫМИ ОБЛАКАМИ
    // =============================================
    function addStyles() {
        if (document.getElementById('weather-ultimate-styles')) return;

        const styles = `
            /* ПЛАВНЫЕ ПЕРЕХОДЫ ФОНА */
            #welcome-card, #weather-bg {
                transition: background 1.5s ease-in-out !important;
            }

            /* ОГРОМНЫЕ ПУШИСТЫЕ ОБЛАКА */
            .fluffy-cloud {
                position: absolute;
                pointer-events: none;
                z-index: 1;
                opacity: 0;
                animation-fill-mode: both;
                will-change: transform, opacity;
                filter: blur(var(--cloud-blur, 10px));
            }

            .massive-cloud {
                filter: blur(var(--cloud-blur, 15px)) brightness(1.1);
            }

            .cloud-blob {
                position: absolute;
                background: white;
                border-radius: 50%;
                filter: blur(var(--blob-blur, 5px));
                opacity: var(--blob-opacity, 0.3);
                transform-origin: center center;
            }

            /* АНИМАЦИИ ДЛЯ ОГРОМНЫХ ОБЛАКОВ */
            @keyframes floatGently {
                0%, 100% {
                    transform:
                        translate(calc(var(--float-x, 0) * 1px),
                                 calc(var(--float-y, 0) * 1px))
                        scale(1)
                        rotate(calc(var(--rotate-start, 0) * 1deg));
                    opacity: var(--opacity-start, 0.3);
                }
                25% {
                    transform:
                        translate(calc(var(--float-x, 0) * 1px + 20px),
                                 calc(var(--float-y, 0) * 1px - 15px))
                        scale(1.08)
                        rotate(calc(var(--rotate-start, 0) * 1deg + 1.5deg));
                    opacity: var(--opacity-peak, 0.5);
                }
                50% {
                    transform:
                        translate(calc(var(--float-x, 0) * 1px + 8px),
                                 calc(var(--float-y, 0) * 1px + 10px))
                        scale(0.95)
                        rotate(calc(var(--rotate-start, 0) * 1deg - 1deg));
                    opacity: var(--opacity-start, 0.3);
                }
                75% {
                    transform:
                        translate(calc(var(--float-x, 0) * 1px - 15px),
                                 calc(var(--float-y, 0) * 1px + 12px))
                        scale(1.04)
                        rotate(calc(var(--rotate-start, 0) * 1deg + 1.2deg));
                    opacity: var(--opacity-mid, 0.4);
                }
            }

            @keyframes flyMassiveAcross {
                0% {
                    transform:
                        translateX(calc(var(--start-x, -100) * 1px))
                        translateY(calc(var(--float-y, 0) * 1px))
                        scale(0.85);
                    opacity: 0;
                }
                5% {
                    opacity: var(--opacity-start, 0.3);
                    transform: scale(0.9);
                }
                15% {
                    opacity: var(--opacity-peak, 0.5);
                    transform: scale(1);
                }
                30%, 70% {
                    opacity: var(--opacity-peak, 0.5);
                    transform: scale(1.05);
                }
                85% {
                    opacity: var(--opacity-start, 0.3);
                    transform: scale(1);
                }
                95% {
                    opacity: 0.1;
                    transform: scale(0.95);
                }
                100% {
                    transform:
                        translateX(calc(100vw + var(--start-x, 100) * 1px + 300px))
                        translateY(calc(var(--float-y, 0) * 1px + var(--drift-y, 50) * 1px))
                        scale(0.9);
                    opacity: 0;
                }
            }

            /* ДЫМКА */
            .haze-layer {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(
                    to bottom,
                    rgba(255, 255, 255, 0.03) 0%,
                    rgba(255, 255, 255, 0.12) 20%,
                    rgba(255, 255, 255, 0.05) 40%,
                    transparent 60%,
                    rgba(255, 255, 255, 0.02) 80%,
                    transparent 100%
                );
                z-index: 0;
                pointer-events: none;
                animation: hazeShift 40s infinite alternate ease-in-out;
                filter: blur(5px);
            }

            @keyframes hazeShift {
                0% {
                    opacity: 0.4;
                    transform: translateY(0) scale(1);
                }
                33% {
                    opacity: 0.6;
                    transform: translateY(-15px) scale(1.03);
                }
                66% {
                    opacity: 0.5;
                    transform: translateY(10px) scale(0.97);
                }
                100% {
                    opacity: 0.45;
                    transform: translateY(5px) scale(1.01);
                }
            }

            /* ВСПЛЫВАНИЕ ОГРОМНЫХ ОБЛАКОВ */
            @keyframes cloudAppear {
                0% {
                    opacity: 0;
                    transform: scale(0.7) translateY(30px) rotate(-5deg);
                }
                70% {
                    opacity: 0.8;
                    transform: scale(1.05) translateY(-5px) rotate(2deg);
                }
                100% {
                    opacity: 1;
                    transform: scale(1) translateY(0) rotate(0deg);
                }
            }

            /* СВЕТОВОЙ ОБЪЕМ ДЛЯ ОГРОМНЫХ ОБЛАКОВ */
            .cloud-light {
                position: absolute;
                border-radius: 50%;
                background: radial-gradient(
                    circle at center,
                    rgba(255, 255, 255, 0.5) 0%,
                    rgba(255, 255, 255, 0.15) 50%,
                    transparent 70%
                );
                filter: blur(25px);
                opacity: 0.4;
                z-index: 1;
            }

            /* АНИМАЦИЯ ПЕРЕЛИВА ЦВЕТА */
            @keyframes colorPulse {
                0%, 100% {
                    filter: hue-rotate(0deg) brightness(1) saturate(1);
                }
                50% {
                    filter: hue-rotate(8deg) brightness(1.1) saturate(1.2);
                }
            }

            /* ДРУГИЕ АНИМАЦИИ */
            @keyframes sunGlow {
                0% {
                    box-shadow:
                        0 0 60px rgba(255, 215, 0, 0.9),
                        0 0 120px rgba(255, 215, 0, 0.6),
                        0 0 180px rgba(255, 215, 0, 0.3);
                }
                100% {
                    box-shadow:
                        0 0 80px rgba(255, 215, 0, 1),
                        0 0 160px rgba(255, 215, 0, 0.8),
                        0 0 240px rgba(255, 215, 0, 0.5);
                }
            }

            @keyframes moonFloat {
                0%, 100% {
                    transform: translateY(0) rotate(0deg) scale(1);
                }
                33% {
                    transform: translateY(-20px) rotate(4deg) scale(1.05);
                }
                66% {
                    transform: translateY(10px) rotate(-2deg) scale(0.98);
                }
            }

            @keyframes starTwinkle {
                0%, 100% {
                    opacity: 0.3;
                    transform: scale(1) rotate(0deg);
                }
                50% {
                    opacity: 1;
                    transform: scale(1.3) rotate(180deg);
                }
            }

            @keyframes rainFall {
                0% {
                    transform: translateY(-40px) rotate(10deg);
                    opacity: 0;
                }
                10% {
                    opacity: 1;
                }
                90% {
                    opacity: 1;
                }
                100% {
                    transform: translateY(100vh) rotate(-5deg);
                    opacity: 0;
                }
            }

            @keyframes snowFall {
                0% {
                    transform: translateY(-20px) translateX(0) rotate(0deg);
                }
                100% {
                    transform: translateY(100vh) translateX(var(--sway-distance, 0)) rotate(360deg);
                }
            }

            @keyframes snowSway {
                0% {
                    transform: translateX(0);
                }
                100% {
                    transform: translateX(var(--sway-distance, 40px));
                }
            }

            @keyframes lightningFlash {
                0%, 90%, 100% {
                    opacity: 0;
                }
                5%, 15% {
                    opacity: 0.8;
                }
                10% {
                    opacity: 1;
                }
            }

            @keyframes fogMove {
                0% {
                    transform: translateX(0);
                }
                100% {
                    transform: translateX(-50%);
                }
            }

            /* СТИЛИ ДЛЯ КОНТЕЙНЕРОВ */
            #weather-animation {
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                overflow: visible !important;
                pointer-events: none !important;
                z-index: 1 !important;
            }

            #time-of-day {
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                overflow: visible !important;
                pointer-events: none !important;
                z-index: 2 !important;
            }

            /* ОБЛАКА */
            .slow-cloud {
                z-index: 3 !important;
                animation-timing-function: ease-in-out !important;
            }

            .fast-cloud {
                z-index: 1 !important;
                animation-timing-function: linear !important;
            }

            .sun-animation,
            .moon-animation {
                z-index: 10 !important;
            }

            .star {
                z-index: 5 !important;
            }

            .raindrop,
            .snowflake {
                z-index: 15 !important;
            }

            .lightning-flash {
                z-index: 20 !important;
            }

            .fog-layer {
                z-index: 25 !important;
            }

            /* СТИЛИ ДЛЯ КАРТОЧКИ ПОГОДЫ */
            .weather-info {
                background: rgb(75 72 72 / 35%) !important;
                backdrop-filter: blur(15px) !important;
                transition: all 0.3s ease !important;
                border-radius: 15px !important;
                max-width: 350px !important;
            }

            .weather-icon {
                font-size: 2.5rem !important;
                filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.4)) !important;
            }

            /* ФОНЫ ВРЕМЕНИ СУТОК С ДЫМКОЙ */
            #welcome-card.midnight-bg,
            #weather-bg.midnight-bg {
                background: linear-gradient(135deg, #000000 0%, #0A0A0A 25%, #141414 66%, #282825 100%) !important;
            }
            #welcome-card.midnight-bg::before,
            #weather-bg.midnight-bg::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background:
                    radial-gradient(circle at 20% 30%, rgba(100, 100, 120, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 70%, rgba(80, 80, 100, 0.05) 0%, transparent 50%),
                    radial-gradient(circle at 50% 50%, rgba(60, 60, 80, 0.03) 0%, transparent 70%);
                z-index: 0;
                filter: blur(20px);
            }

            #welcome-card.dawn-bg,
            #weather-bg.dawn-bg {
                background: linear-gradient(135deg, #0F2027 0%, #2C5364 25%, #FF9966 66%, #FFD89B 100%) !important;
            }
            #welcome-card.dawn-bg::before,
            #weather-bg.dawn-bg::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background:
                    radial-gradient(circle at 30% 40%, rgba(255, 150, 100, 0.15) 0%, transparent 60%),
                    radial-gradient(circle at 70% 60%, rgba(255, 200, 150, 0.08) 0%, transparent 50%),
                    radial-gradient(circle at 10% 90%, rgba(255, 180, 120, 0.05) 0%, transparent 70%);
                z-index: 0;
                filter: blur(25px);
            }

            #welcome-card.morning-bg,
            #weather-bg.morning-bg {
                background: linear-gradient(135deg, #FFD89B 0%, #FF9966 25%, #4C9AFF 100%) !important;
            }

            #welcome-card.day-bg,
            #weather-bg.day-bg {
                background: linear-gradient(135deg, #1E90FF 0%, #4C9AFF 50%, #6495ED 100%) !important;
            }
            #welcome-card.day-bg::before,
            #weather-bg.day-bg::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background:
                    radial-gradient(circle at 20% 80%, rgba(255, 255, 255, 0.15) 0%, transparent 40%),
                    radial-gradient(circle at 80% 20%, rgba(200, 230, 255, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 50% 50%, rgba(150, 200, 255, 0.05) 0%, transparent 70%);
                z-index: 0;
                filter: blur(30px);
            }

            #welcome-card.evening-bg,
            #weather-bg.evening-bg {
                background: linear-gradient(135deg, #FF7E5F 0%, #FEB47B 33%, #8A2BE2 66%, #4B0082 100%) !important;
            }
            #welcome-card.evening-bg::before,
            #weather-bg.evening-bg::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background:
                    radial-gradient(circle at 40% 30%, rgba(255, 120, 80, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 60% 70%, rgba(150, 80, 255, 0.1) 0%, transparent 60%),
                    radial-gradient(circle at 20% 50%, rgba(255, 100, 150, 0.05) 0%, transparent 70%);
                z-index: 0;
                filter: blur(35px);
            }

            #welcome-card.night-bg,
            #weather-bg.night-bg {
                background: linear-gradient(135deg, #0F2027 0%, #203A43 33%, #2C5364 66%, #282825 100%) !important;
            }
        `;

        const styleEl = document.createElement('style');
        styleEl.id = 'weather-ultimate-styles';
        styleEl.textContent = styles;
        document.head.appendChild(styleEl);
        console.log('✅ Стили с ОГРОМНЫМИ облаками добавлены');
    }

    // =============================================
    // ЭКСПОРТ ДЛЯ ОТЛАДКИ
    // =============================================
    window.weatherUltimate = {
        getTimeOfDay,
        applyTimeOfDayBackground,
        updateWeather,
        showRealWeather,
        createGiantFluffyCloud,
        createGiantCloudSky,
        CONFIG,
        TIME_OF_DAY_BACKGROUNDS,
        ANIMATIONS,
        CLOUD_TYPES
    };

    console.log('🚀🌪️ ULTIMATE погодный виджет с ОГРОМНЫМИ пушистыми облаками готов!');

})();