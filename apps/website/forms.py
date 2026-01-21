from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import ParserSettings, UserProfile


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'required': 'required'
        }),
        label='Email адрес'
    )

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иван',
            'required': 'required'
        }),
        label='Имя'
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов',
            'required': 'required'
        }),
        label='Фамилия'
    )

    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        }),
        label='Телефон'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'username',
                'required': 'required'
            }),
        }
        labels = {
            'username': 'Имя пользователя',
        }
        help_texts = {
            'username': 'Только английские буквы, цифры и символы @/./+/-/_',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Настраиваем поля паролей
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Минимум 8 символов',
            'required': 'required'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Повторите пароль',
            'required': 'required'
        })

        # Убираем стандартные help_text для паролей (они будут в шаблоне)
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            # Создаем профиль пользователя
            UserProfile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone', '')
            )

        return user


class ParserSettingsForm(forms.ModelForm):
    # 🔥 ДОБАВЛЕНО ПОЛЕ ГОРОДА
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Начните вводить город...',
            'id': 'id_city',
            'autocomplete': 'off'
        }),
        label='Город поиска',
        help_text="Город для поиска товаров. Для Auto.ru оставьте пустым."
    )

    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Использовать по умолчанию',
        help_text="Только одни настройки могут быть по умолчанию"
    )

    keywords = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Видеокарта, iPhone, кроссовки...',
            'class': 'form-control'
        }),
        help_text="Ключевые слова через запятую"
    )

    exclude_keywords = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'б/у, сломан, нерабочий...',
            'class': 'form-control'
        }),
        label='Исключить слова',
        help_text="Товары содержащие эти слова будут пропущены"
    )

    browser_windows = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5',
            'placeholder': '1',
            'required': 'required'
        }),
        label='Количество окон браузера',
        help_text="Увеличивает скорость поиска (1-5 окон)"
    )

    # 🔥 ДОБАВЛЕНО ПОЛЕ ДЛЯ ВЫБОРА САЙТА
    site = forms.ChoiceField(
        choices=ParserSettings.SITE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': 'required',
            'id': 'site_select'
        }),
        label='Сайт для поиска',
        help_text="Выберите сайт для парсинга"
    )

    class Meta:
        model = ParserSettings
        fields = [
            'name', 'keywords', 'exclude_keywords', 'min_price', 'max_price',
            'min_rating', 'seller_type', 'check_interval', 'max_items_per_hour',
            'browser_windows', 'is_active', 'is_default', 'site', 'city'  # 🔥 ДОБАВЛЕНО 'city'!
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название настроек',
                'required': 'required'
            }),
            'min_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'required': 'required'
            }),
            'max_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1000000',
                'required': 'required'
            }),
            'min_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'max': '5',
                'placeholder': '4.0',
                'required': 'required'
            }),
            'seller_type': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
            'check_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'max': '1440',
                'placeholder': '30 минут',
                'required': 'required'
            }),
            'max_items_per_hour': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100',
                'placeholder': '10',
                'required': 'required'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Название настроек',
            'keywords': 'Ключевые слова',
            'exclude_keywords': 'Исключить слова',
            'min_price': 'Минимальная цена',
            'max_price': 'Максимальная цена',
            'min_rating': 'Минимальный рейтинг',
            'seller_type': 'Тип продавца',
            'check_interval': 'Интервал проверки (минуты)',
            'max_items_per_hour': 'Максимум товаров в час',
            'browser_windows': 'Окон браузера',
            'is_active': 'Автопоиск активен',
            'city': 'Город поиска',  # 🔥 ДОБАВЛЕН ЛЕЙБЛ
            'site': 'Сайт для поиска',
        }
        help_texts = {
            'exclude_keywords': 'Товары содержащие эти слова будут пропущены при поиске',
            'browser_windows': 'Увеличивает скорость поиска за счет параллельной обработки',
            'city': 'Город для поиска товаров. Для Auto.ru оставьте пустым.',  # 🔥 ДОБАВЛЕНА ПОДСКАЗКА
            'site': 'Выберите сайт для парсинга объявлений',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 Устанавливаем значение по умолчанию для города
        if self.instance and self.instance.city:
            self.fields['city'].initial = self.instance.city
        else:
            self.fields['city'].initial = 'Москва'

        # 🔥 Добавляем класс для отключения поля при Auto.ru
        if self.instance and self.instance.site == 'auto.ru':
            self.fields['city'].widget.attrs.update({
                'disabled': 'disabled',
                'title': 'Для Auto.ru город не используется'
            })

    def clean_city(self):
        """Валидация города"""
        city = self.cleaned_data.get('city', '').strip()

        # Для Auto.ru город должен быть пустым
        site = self.cleaned_data.get('site', 'avito')
        if site == 'auto.ru' and city:
            raise forms.ValidationError('Для Auto.ru город не используется - оставьте поле пустым')

        # Для Avito если город пустой - ставим Москва
        if site == 'avito' and not city:
            city = 'Москва'

        return city

    def clean_min_price(self):
        min_price = self.cleaned_data.get('min_price')
        max_price = self.cleaned_data.get('max_price')

        if min_price and max_price and min_price >= max_price:
            raise forms.ValidationError('Минимальная цена должна быть меньше максимальной')

        if min_price < 0:
            raise forms.ValidationError('Цена не может быть отрицательной')

        return min_price

    def clean_max_price(self):
        min_price = self.cleaned_data.get('min_price')
        max_price = self.cleaned_data.get('max_price')

        if min_price and max_price and max_price <= min_price:
            raise forms.ValidationError('Максимальная цена должна быть больше минимальной')

        if max_price < 0:
            raise forms.ValidationError('Цена не может быть отрицательной')

        return max_price

    def clean_min_rating(self):
        min_rating = self.cleaned_data.get('min_rating')
        if min_rating is not None:
            if min_rating < 0 or min_rating > 5:
                raise forms.ValidationError('Рейтинг должен быть от 0 до 5')
        return min_rating

    def clean_check_interval(self):
        check_interval = self.cleaned_data.get('check_interval')
        if check_interval < 5:
            raise forms.ValidationError('Интервал проверки не может быть меньше 5 минут')
        if check_interval > 1440:
            raise forms.ValidationError('Интервал проверки не может быть больше 24 часов')
        return check_interval

    def clean_browser_windows(self):
        browser_windows = self.cleaned_data.get('browser_windows')
        if browser_windows < 1 or browser_windows > 5:
            raise forms.ValidationError('Количество окон должно быть от 1 до 5')
        return browser_windows

    def clean_site(self):
        """Валидация выбора сайта"""
        site = self.cleaned_data.get('site')
        valid_sites = [choice[0] for choice in ParserSettings.SITE_CHOICES]
        if site not in valid_sites:
            raise forms.ValidationError('Выбран неподдерживаемый сайт')
        return site

    def clean(self):
        cleaned_data = super().clean()
        keywords = cleaned_data.get('keywords')
        exclude_keywords = cleaned_data.get('exclude_keywords')
        site = cleaned_data.get('site', 'avito')
        city = cleaned_data.get('city', '')

        # Проверка на конфликтующие слова
        if keywords and exclude_keywords:
            keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
            exclude_list = [k.strip().lower() for k in exclude_keywords.split(',') if k.strip()]

            conflicting_words = set(keyword_list) & set(exclude_list)
            if conflicting_words:
                raise forms.ValidationError(
                    f'Слова не могут быть одновременно в ключевых и исключаемых: {", ".join(conflicting_words)}'
                )

        # 🔥 Дополнительная проверка для Auto.ru
        if site == 'auto.ru' and city and city != 'Москва':
            raise forms.ValidationError('Для Auto.ru поиск выполняется по всей России, город не используется')

        return cleaned_data