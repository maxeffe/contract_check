# Contract Analysis System

Система анализа договоров с использованием модели с Хагинфейс.

## Описание проекта

Contract Analysis System - это микросервисная архитектура для анализа договоров, включающая:

- **FastAPI Backend** - REST API для обработки запросов и управления данными
- **Streamlit Frontend** - веб-интерфейс для взаимодействия с пользователями
- **ML Workers** - асинхронные воркеры для машинного обучения
- **PostgreSQL** - база данных для хранения информации
- **RabbitMQ** - очередь сообщений для асинхронной обработки
- **Nginx** - обратный прокси и балансировщик нагрузки

## Архитектура

```
Frontend (Streamlit) ←→ Nginx ←→ FastAPI Backend ←→ PostgreSQL
                                       ↓
                                   RabbitMQ ←→ ML Workers
```

## Технический стек

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Streamlit, Plotly
- **ML**: HuggingFace Transformers
- **Database**: PostgreSQL
- **Message Queue**: RabbitMQ
- **Containerization**: Docker, Docker Compose
- **Web Server**: Nginx

## Запуск проекта

### Предварительные требования

- Docker
- Docker Compose
- Git

### Инструкция по запуску

1. **Клонирование репозитория**
   ```bash
   git clone <repository-url>
   cd mldev
   ```

2. **Настройка переменных окружения**
   ```bash
   cp .env.template .env
   cp app/.env.example app/.env
   ```
   
   Заполните значения в файлах `.env` и `app/.env`:
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - настройки PostgreSQL
   - `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` - настройки RabbitMQ
   - `API_ANALITICS` - ключ для аналитики
   - `HUGGINGFACE_API_TOKEN` - токен для HuggingFace API

3. **Запуск всех сервисов**
   ```bash
   docker-compose up -d
   ```

4. **Проверка работоспособности**
   - API документация: http://localhost/docs
   - Веб-интерфейс: http://localhost
   - RabbitMQ Management: http://localhost:15672
   - Streamlit фронтенд: http://localhost:8501

### Структура портов

- **80/443**: Nginx (веб-интерфейс и API)
- **8000**: FastAPI (прямой доступ)
- **5432**: PostgreSQL
- **5672**: RabbitMQ
- **15672**: RabbitMQ Management UI

## Разработка

### Локальный запуск для разработки

1. **Backend**
   ```bash
   cd app
   pip install -r requirements.txt
   python api.py
   ```

2. **Frontend**
   ```bash
   cd streamlit-frontend
   pip install -r requirements.txt
   streamlit run app.py
   ```

3. **ML Worker**
   ```bash
   cd app
   python ml_worker.py worker-dev
   ```

### Тестирование

```bash
cd app
pytest tests/
```

## Основные функции

- **Аутентификация и авторизация пользователей**
- **Загрузка документов**
- **Саммаризация текста документов, выделение рисков и финальный скор риска договора**
- **Система кошельков и транзакций**
- **История операций**

## API Endpoints

- `POST /auth/register` - регистрация пользователя
- `POST /auth/login` - авторизация
- `POST /predict/` - создание задачи анализа
- `GET /predict/{job_id}` - получение результата
- `GET /wallet/balance` - баланс кошелька
- `POST /wallet/transaction` - создание транзакции
