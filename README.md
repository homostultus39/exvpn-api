# ExVPN - синоним к слову надежность

ExVPN API для управления AmneziaWG протоколом на базе FastAPI.

## Структура проекта

```
exvpn-api/
├── src/
│   ├── api/v1/          # API endpoints
│   ├── database/        # Модели БД и подключение
│   ├── redis/           # Redis клиент
│   ├── minio/           # MinIO клиент
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
- SSH доступ к серверу (нужен клиенту AmneziaVPN для проверки установленных контейнеров)

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

### 3. Создание необходимых директорий

Перед запуском необходимо создать директорию для конфигурационных файлов AmneziaWG на хосте:

```bash
sudo mkdir -p /opt/amnezia/awg
sudo chown -R $USER:$USER /opt/amnezia
sudo chmod 755 /opt/amnezia
```

**Важно**: Эта директория монтируется в контейнер API через bind mount, поэтому она должна существовать на хосте до запуска docker-compose. API контейнер будет читать и записывать конфигурационные файлы AmneziaWG в эту директорию, что позволяет синхронизировать данные между API и контейнером AmneziaWG.

### 4. Запуск через Docker Compose

```bash
docker-compose up -d
```

### 4.1. Требования для подключения из AmneziaVPN

Клиент AmneziaVPN использует SSH для проверки установленных контейнеров и чтения конфигурации сервера. Убедитесь, что:

- На сервере доступен SSH.
- Есть пользователь с правами на выполнение `docker ps`, `docker inspect`, `docker exec` через `sudo` без пароля.
- Контейнер AmneziaWG имеет имя `amnezia-awg` (это имя используется клиентом).

API будет доступен по адресу: http://localhost:8000

### 5. Применение миграций

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
