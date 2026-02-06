import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

class SqlQueryGenerator:
    def __init__(
            self, 
            api_key: str, 
            model: str = "arcee-ai/trinity-large-preview:free",
            base_url: str = "https://openrouter.ai/api/v1/chat/completions",
            max_tokens: int = 1000
        ):
                        
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self._DEFAULT_SYSTEM_PROMPT: str = "Ты — опытный SQL-разработчик PostgreSQL."
        self._DEFAULT_USER_PROMPT: str = (        
            """
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
            """
        )
        
    async def generate_query(self, user_query: str) -> str:
        logger.info(f"Генерация SQL для запроса: {user_query}")
        
        full_prompt = self._DEFAULT_USER_PROMPT.format(user_query=user_query)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": self.max_tokens
        }

        timeout = aiohttp.ClientTimeout(total=180)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                logger.debug(f"Отправка запроса к LLM API: {self.model}")
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    raw_text = await response.text()
                    
                    if response.status == 200:
                        result = await response.json()
                        if "choices" in result and result["choices"]:
                            sql_response = result["choices"][0]["message"]["content"].strip()
                            sql_response = sql_response.replace('```sql', '').replace('```', '').strip()
                            logger.info(f"LLM вернул SQL: {sql_response}")
                            return sql_response
                        else:
                            logger.error(f"Пустой ответ от LLM API: {raw_text}")
                            raise RuntimeError("Пустой ответ от API")
                    else:
                        logger.error(f"Ошибка LLM API ({response.status}): {raw_text}")
                        raise RuntimeError(f"Ошибка API ({response.status})")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Ошибка сети при обращении к LLM: {e}")
                raise RuntimeError(f"Ошибка сети: {e}") from e
            except asyncio.TimeoutError:
                logger.error("Таймаут запроса к LLM (180 сек)")
                raise RuntimeError("Таймаут запроса: превышено время ожидания (180 сек).")