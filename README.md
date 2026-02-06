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
1. Все даты и время в БД хранятся в UTC (+00:00)
2. Для фильтрации по дате видео используй DATE(video_created_at)
3. Для фильтрации по дате снапшотов используй DATE(created_at)
4. Для фильтрации по точному времени внутри дня указывай часовой пояс UTC (+00):
- created_at >= '2025-11-28 10:00:00+00'
- created_at < '2025-11-28 15:00:00+00'
5. Для фильтрации по периоду дат используй диапазон с UTC:
- video_created_at >= '2025-11-01 00:00:00+00'
- video_created_at < '2025-11-06 00:00:00+00'
6. В таблице video_snapshots НЕТ поля creator_id. Для фильтрации снапшотов по креатору используй JOIN с таблицей videos
7. Всегда используй '<' вместо '<=' для верхней границы временного интервала

ДАТЫ в русском формате конвертируй в SQL-формат:
- "28 ноября 2025" -> DATE(column) = '2025-11-28'
- "с 3 по 10 ноября 2025 включительно" -> column >= '2025-11-03 00:00:00+00' AND column < '2025-11-10 00:00:00+00'
- "с 7:00 до 11:00 25 ноября 2025" -> column >= '2025-11-25 07:00:00+00' AND column < '2025-11-25 11:00:00+00' AND DATE(column) = '2025-11-28'

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {user_query}

SQL-ЗАПРОС (ТОЛЬКО КОД):
            
## Логирование
bot.log - логи работы бота
setup.log - логи инициализации базы данных