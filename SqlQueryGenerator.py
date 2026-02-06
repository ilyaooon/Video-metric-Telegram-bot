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