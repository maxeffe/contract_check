# 📄 Анализатор Договоров - Streamlit Frontend

Веб-интерфейс на Streamlit для системы интеллектуального анализа договоров с использованием машинного обучения.

## 🚀 Возможности

### 🔐 Аутентификация
- Вход и регистрация пользователей
- JWT токены для безопасности
- Автоматическое обновление сессий

### 📝 Анализ документов
- Загрузка файлов (TXT, PDF, DOC, DOCX)
- Ввод текста вручную
- Поддержка русского и английского языков
- Выбор различных ML моделей
- Краткий и подробный анализ

### 📊 Управление данными
- История всех анализов
- Интерактивные графики и статистика
- Фильтрация по статусам и датам
- Экспорт данных в CSV и TXT

### 💳 Финансовая система
- Управление балансом кошелька
- Пополнение счета
- История транзакций
- Автоматическое списание/возврат средств

### 📈 Визуализация
- Круговые диаграммы распределения статусов
- Гистограммы риск-индексов
- Временные графики затрат
- Интерактивные метрики

## 🛠️ Технические требования

### Системные требования
- Python 3.8+
- 512 МБ оперативной памяти
- 50 МБ свободного места на диске

### Зависимости
- Streamlit 1.28.0
- Requests 2.31.0
- Pandas 2.1.0
- Plotly 5.16.0
- Python-dotenv 1.0.0

## 📦 Установка и настройка

### 1. Установка зависимостей

```bash
# Перейдите в директорию проекта
cd C:\Users\PC\Python_Pr\mldev\streamlit-frontend

# Создайте виртуальное окружение (рекомендуется)
python -m venv venv

# Активируйте виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 2. Настройка конфигурации

Отредактируйте файл `.env`:

```env
# URL FastAPI сервера (по умолчанию)
API_BASE_URL=http://localhost:8000

# Настройки Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### 3. Запуск приложения

```bash
# Базовый запуск
streamlit run app.py

# Запуск с настройками из .env
streamlit run app.py --server.port=8501 --server.address=0.0.0.0

# Запуск в режиме разработки
streamlit run app.py --server.runOnSave=true
```

### 4. Доступ к приложению

После запуска приложение будет доступно по адресу:
- **Локально:** http://localhost:8501
- **В сети:** http://[YOUR_IP]:8501

## 🏗️ Структура проекта

```
streamlit-frontend/
├── app.py                    # Главный файл приложения
├── pages/                    # Страницы приложения
│   ├── New_Analysis.py      # Создание нового анализа
│   ├── History.py           # История анализов
│   └── Wallet.py            # Управление кошельком
├── services/                 # Сервисы
│   ├── api_client.py        # API клиент для FastAPI
│   └── auth_service.py      # Сервис аутентификации
├── components/               # Компоненты UI
│   └── visualization.py     # Визуализация данных
├── utils/                    # Утилиты
│   └── helpers.py           # Вспомогательные функции
├── requirements.txt          # Зависимости Python
├── .env                     # Переменные окружения
└── README.md                # Документация
```

## 🎯 Использование

### Первый запуск

1. **Убедитесь, что FastAPI сервер запущен** (по умолчанию на http://localhost:8000)
2. **Запустите Streamlit приложение**
3. **Откройте браузер** и перейдите на http://localhost:8501
4. **Зарегистрируйтесь** или **войдите** в существующий аккаунт

### Создание анализа

1. Перейдите в раздел **"📝 Новый анализ"**
2. Выберите способ ввода:
   - **Ввод текста вручную** - вставьте текст договора
   - **Загрузка файла** - выберите файл с компьютера
3. Настройте параметры:
   - **Язык документа** (русский, английский, автоопределение)
   - **Модель анализа** (различные ML модели с разной стоимостью)
   - **Глубина анализа** (краткий или подробный)
4. Проверьте **оценку стоимости**
5. Нажмите **"🚀 Запустить анализ"**

### Просмотр результатов

1. Перейдите в раздел **"📋 История"**
2. Найдите нужный анализ в списке
3. Кликните для просмотра подробностей:
   - **Сводка анализа**
   - **Риск-индекс** документа
   - **Выявленные рисковые пункты**
   - **Рекомендации**
4. Экспортируйте результаты при необходимости

### Управление балансом

1. Перейдите в раздел **"💳 Кошелек"**
2. Проверьте **текущий баланс**
3. При необходимости **пополните счет**:
   - Введите сумму вручную
   - Или используйте быстрые суммы
4. Просматривайте **историю транзакций**
5. Экспортируйте **финансовые отчеты**

## ⚙️ Настройка и конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `API_BASE_URL` | URL FastAPI сервера | `http://localhost:8000` |
| `STREAMLIT_SERVER_PORT` | Порт Streamlit | `8501` |
| `STREAMLIT_SERVER_ADDRESS` | Адрес привязки | `0.0.0.0` |

### Настройки Streamlit

Создайте файл `.streamlit/config.toml` для дополнительных настроек:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[server]
maxUploadSize = 10
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

## 🔧 Разработка и расширение

### Добавление новой страницы

1. Создайте файл в папке `pages/`
2. Импортируйте необходимые модули:
```python
from services.auth_service import check_authentication, show_user_info
from services.api_client import get_api_client
```

3. Добавьте проверку авторизации:
```python
if check_authentication():
    show_user_info()
else:
    st.error("🔒 Для доступа к этой странице необходимо войти в систему")
    st.stop()
```

### Добавление нового API метода

В `services/api_client.py`:
```python
def new_api_method(self, param1, param2):
    response = self.session.post(
        f"{self.base_url}/new/endpoint",
        json={"param1": param1, "param2": param2},
        headers=self._get_auth_headers()
    )
    return self._handle_response(response)
```

### Кастомизация интерфейса

Используйте CSS в Streamlit:
```python
st.markdown("""
<style>
.custom-class {
    color: #1f77b4;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)
```

## 🐛 Устранение неисправностей

### Частые проблемы

#### 1. Ошибка подключения к API
```
❌ Ошибка загрузки данных: Connection refused
```
**Решение:** Убедитесь, что FastAPI сервер запущен на правильном порту.

#### 2. Ошибка аутентификации
```
🔒 Сессия истекла. Пожалуйста, войдите заново.
```
**Решение:** Перезайдите в систему через главную страницу.

#### 3. Ошибка загрузки файла
```
❌ Файл слишком большой (максимум 10 МБ)
```
**Решение:** Уменьшите размер файла или разделите его на части.

#### 4. Проблемы с отображением
```
DuplicateWidgetID: There are multiple widgets with the same generated key
```
**Решение:** Добавьте уникальные `key` параметры к виджетам.

### Логи и отладка

Включите отладочный режим в Streamlit:
```bash
streamlit run app.py --server.enableCORS=false --logger.level=debug
```

Просматривайте логи в браузере:
- Откройте Developer Tools (F12)
- Перейдите на вкладку Console
- Проверьте Network для API запросов

## 📈 Производительность

### Оптимизация кеширования

Используйте правильные TTL для кеширования:
```python
@st.cache_data(ttl=300)  # 5 минут для статичных данных
def load_models():
    return api_client.get_available_models()

@st.cache_data(ttl=30)   # 30 секунд для динамичных данных
def load_wallet_info():
    return api_client.get_wallet_info()
```

### Ограничение загрузки данных

Используйте пагинацию для больших наборов данных:
```python
limit = st.selectbox("Показать записей:", [10, 20, 50, 100])
data = api_client.get_prediction_history(limit=limit)
```

## 🔒 Безопасность

### JWT токены
- Токены хранятся в `st.session_state`
- Автоматическое обновление при истечении
- Безопасная передача в заголовках запросов

### Валидация данных
- Проверка размера загружаемых файлов
- Валидация типов файлов
- Санитизация пользовательского ввода

### HTTPS
Для продакшена настройте HTTPS:
```bash
streamlit run app.py --server.port=443 --server.sslCertFile=cert.pem --server.sslKeyFile=key.pem
```

## 🚀 Развертывание в продакшн

### Docker контейнер

Создайте `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

### Systemd сервис

Создайте `/etc/systemd/system/contract-analyzer-frontend.service`:
```ini
[Unit]
Description=Contract Analyzer Frontend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/streamlit-frontend
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/streamlit run app.py --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи** приложения
2. **Убедитесь в доступности** FastAPI сервера
3. **Проверьте переменные окружения**
4. **Обновите зависимости** до последних версий

## 📄 Лицензия

Этот проект создан для демонстрационных целей. Все права защищены.

---

## 🎉 Готово к работе!

Ваш Streamlit интерфейс готов к работе. Наслаждайтесь удобным и интуитивным анализом договоров! 🚀