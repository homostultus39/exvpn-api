# ExVPN - синоним к слову надежность

API для управления AmneziaWG протоколом на базе FastAPI.

## Структура проекта

```
exvpn-api/
├── src/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Безопасность, исключения
│   ├── database/        # Модели БД и подключение
│   ├── redis/           # Redis клиент
│   ├── minio/           # MinIO клиент
│   ├── schemas/         # Pydantic схемы
│   ├── services/        # Бизнес-логика
│   └── utils/           # Утилиты и настройки
├── migrations/          # Alembic миграции
├── tests/              # Тесты
├── docker-compose.yml  # Docker Compose конфигурация
├── Dockerfile          # Docker образ API
└── .env.prod          # Переменные окружения
```

## Требования

- Python 3.13+
- Poetry
- Docker & Docker Compose

## Установка и запуск

### 1. Установка зависимостей

```bash
poetry install
```

### 2. Настройка переменных окружения

Отредактируйте файл `.env.prod` и укажите свои значения:

```bash
# Сгенерируйте секретные ключи
python -c "import secrets; print(secrets.token_urlsafe(32))"  # для SECRET_KEY и JWT_SECRET_KEY

# Сгенерируйте Fernet ключ для шифрования
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Запуск через Docker Compose

```bash
docker-compose up -d
```

API будет доступен по адресу: http://localhost:8000

### 4. Применение миграций

После первого запуска примените миграции БД:

```bash
docker-compose exec api alembic upgrade head
```

## API Документация

После запуска документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Health Check

Проверка состояния API:

```bash
curl http://localhost:8000/health
```

## Разработка

### Создание новой миграции

```bash
poetry run alembic revision --autogenerate -m "описание изменений"
```

### Применение миграций

```bash
poetry run alembic upgrade head
```

### Откат миграции

```bash
poetry run alembic downgrade -1
```

### Запуск тестов

```bash
poetry run pytest
```

## Сервисы

- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MinIO Console**: http://localhost:9001

## Статус разработки

✅ Track 1: Базовая инфраструктура и настройка окружения - завершен
✅ Track 3: Модели базы данных и схемы - завершен

### Следующие шаги

- Track 2: Подключения к внешним сервисам (Redis, MinIO)
- Track 4: Безопасность и авторизация
- Track 5: Утилиты и сервисы
- Track 6: AWG Service и Config Service
- Track 7: Server API Endpoints
- Track 8: Client API Endpoints
- Track 9: Тестирование и документация
