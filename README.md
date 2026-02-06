# Telegram бот для аналитики видео

## Требования
- Python 3.9+
- PostgreSQL 13+
- API ключ OpenRouter (бесплатный: https://openrouter.ai)
- Токен Telegram бота (получить у @BotFather)

## Загрузка JSON в базу данных
    bash
python database/setup_database.py путь_к_файлу_json

## Установка
1. Установите зависимости:
    bash
pip install -r requirements.txt

2. Настройте переменные окружения в файле .env:
TELEGRAM_TOKEN=ваш_токен_бота
OPENROUTER_API_KEY=ваш_ключ_openrouter
DATABASE_URL=postgresql+asyncpg://пользователь:пароль@ip-адрес:порт/videosdb

3. Создайте базу данных PostgreSQL:
    bash
createdb videosdb

4. Загрузите данные:
    bash
python database/setup_database.py путь_к_файлу

5. Запустите бота:
    bash
python bot.py

## Архитектура проекта
    project/
        bot.py                  # Основной файл бота (обработчик сообщений)
        SqlQueryGenerator.py    # Генератор SQL через LLM API
        database/
            database.py         # Работа с базой данных
            setup_database.py   # Скрипт инициализации БД
            models.py           # SQLAlchemy модели
        requirements.txt        # Зависимости Python
        README.md               # Документация

## Компоненты системы
1. Telegram Bot (bot.py)
Принимает текстовые сообщения от пользователей
Обрабатывает команды (/start, /status)
Управляет потоком запросов

2. SQL Generator (SqlQueryGenerator.py)
Отправляет запросы к LLM API (OpenRouter)
Текущая LLM - Arcee AI: Trinity Large Preview
Преобразует естественный язык в SQL-запросы
Обрабатывает ошибки API

3. Database Layer (database.py, models.py)
Асинхронное подключение к PostgreSQL
Модели данных для видео и снапшотов
Безопасное выполнение SQL-запросов

4. Security Layer
Проверка SQL-запросов на безопасность
Защита от SQL-инъекций
Логирование всех операций

## Промт для LLM
1. Системный промт:
Ты — опытный SQL-разработчик PostgreSQL.

2. Пользовательский промт:
СХЕМА БАЗЫ ДАННЫХ:
1. ТАБЛИЦА videos:
- id (UUID) - идентификатор видео
- creator_id (VARCHAR) - идентификатор креатора (пример: 'aca1061a9d324ecf8c3fa2bb32d7be63')
- video_created_at (TIMESTAMPTZ) - дата и время публикации видео
- views_count (BIGINT) - финальное количество просмотров
- likes_count (BIGINT) - финальное количество лайков
- comments_count (BIGINT) - финальное количество комментариев
- reports_count (BIGINT) - финальное количество жалоб
- created_at (TIMESTAMPTZ)
- updated_at (TIMESTAMPTZ)

2. ТАБЛИЦА video_snapshots:
- id (VARCHAR) - идентификатор снапшота
- video_id (UUID) - ссылка на видео
- views_count (BIGINT) - текущее количество просмотров
- likes_count (BIGINT) - текущее количество лайков
- comments_count (BIGINT) - текущее количество комментариев
- reports_count (BIGINT) - текущее количество жалоб
- delta_views_count (BIGINT) - приращение просмотров с прошлого замера
- delta_likes_count (BIGINT) - приращение лайков с прошлого замера
- delta_comments_count (BIGINT) - приращение комментариев с прошлого замера
- delta_reports_count (BIGINT) - приращение жалоб с прошлого замера
- created_at (TIMESTAMPTZ) - время замера (раз в час)
- updated_at (TIMESTAMPTZ)

ВАЖНО:
1. Для фильтрации по дате в таблице videos (TIMESTAMPTZ) используй преобразование к UTC:
- DATE(video_created_at) = '2025-11-28' -> CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) = '2025-11-28'
- DATE(video_created_at) BETWEEN '2025-11-01' AND '2025-11-05' -> CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) BETWEEN '2025-11-01' AND '2025-11-05'            
АЛЬТЕРНАТИВНО используй диапазон в UTC:
- video_created_at >= '2025-11-01 00:00:00 UTC' AND video_created_at < '2025-11-06 00:00:00 UTC'
2. Для таблицы video_snapshots также используй CAST(created_at AT TIME ZONE 'UTC' AS DATE)
3. creator_id - это строка (VARCHAR), оборачивай в кавычки
4. id видео - UUID, но в SQL используй как строку с кавычками
5. Для уникальных видео используй COUNT(DISTINCT video_id)
6. Для суммирования приростов используй SUM(delta_views_count)

ПРИМЕРЫ SQL:
- "Сколько видео вышло с 1 по 5 ноября 2025?" -> 
SELECT COUNT(*) FROM videos WHERE CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) BETWEEN '2025-11-01' AND '2025-11-05';            
- "На сколько просмотров выросли все видео 28 ноября 2025?" -> 
SELECT SUM(delta_views_count) FROM video_snapshots WHERE CAST(created_at AT TIME ZONE 'UTC' AS DATE) = '2025-11-28';            
- "Сколько разных видео получали новые просмотры 27 ноября 2025?" -> 
SELECT COUNT(DISTINCT video_id) FROM video_snapshots WHERE CAST(created_at AT TIME ZONE 'UTC' AS DATE) = '2025-11-27' AND delta_views_count > 0;

ДАТЫ в русском формате конвертируй в SQL-формат (с учетом UTC):
ВАЖНО: Все даты в БД хранятся в UTC, поэтому используй CAST(column AT TIME ZONE 'UTC' AS DATE)

Для фильтрации по конкретной дате:
- "28 ноября 2025" -> CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) = '2025-11-28'
- "с 1 по 5 ноября 2025 включительно" -> CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) BETWEEN '2025-11-01' AND '2025-11-05'

Для относительных дат:
- "вчера" -> CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) = CURRENT_DATE - INTERVAL '1 day'
- "сегодня" -> CAST(video_created_at AT TIME ZONE 'UTC' AS DATE) = CURRENT_DATE
- "за последнюю неделю" -> video_created_at >= NOW() - INTERVAL '7 days'  # для временного диапазона

Аналогично для таблицы video_snapshots используй CAST(created_at AT TIME ZONE 'UTC' AS DATE)

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {user_query}

SQL-ЗАПРОС (ТОЛЬКО КОД):
            
## Логирование
bot.log - логи работы бота
setup.log - логи инициализации базы данных