import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters.command import Command
from aiogram.types import Message
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from SqlQueryGenerator import SqlQueryGenerator
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import sys
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not all([TELEGRAM_TOKEN, OPENROUTER_API_KEY, DATABASE_URL]):
    logger.error("Не все переменные окружения установлены")
    sys.exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    await message.answer("Введите запрос")

engine = None
AsyncSessionLocal = None

async def init_db():
    global engine, AsyncSessionLocal
    logger.info("Инициализация подключения к БД")
    
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600 
    )
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    logger.info("Подключение к БД инициализировано")

@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Ошибка в сессии БД: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_result(session: AsyncSession, query: str) -> str:
    try:
        logger.info(f"Выполняем SQL: {query[:200]}...")
        result = await session.execute(text(query))
        value = result.scalar()   

        if value is None:
            logger.info("Результат запроса: None")
            return "0"
        
        logger.info(f"Результат запроса: {value}")
        return str(value)
        
    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}, SQL: {query[:200]}...")
        return "0"
    
def is_safe_sql(query: str) -> bool:
    query_lower = query.strip().lower()        
    if not query_lower.startswith('select'):
        return False    
    
    query_clean = re.sub(r'--.*?\n|/\*.*?\*/', '', query_lower, flags=re.DOTALL)    
    
    statements = [s.strip() for s in query_clean.split(';') if s.strip()]
    if len(statements) != 1:
        return False    
   
    statement = statements[0]
    if not statement.startswith('select'):
        return False
    
    dangerous_keywords = [
        r'\binsert\b', r'\bupdate\b', r'\bdelete\b',
        r'\bdrop\b', r'\btruncate\b', r'\bcreate\b',
        r'\balter\b', r'\bgrant\b', r'\brevoke\b',
        r'\bexec(ute)?\b', r'\bunion\b',
        r'information_schema\b', r'pg_',
        r'\bcurrent_user\b', r'\bsession_user\b',
        r'\binto\b\s+(\w+\.)?\w*\s*(\(|values)',
    ]
    
    for pattern in dangerous_keywords:
        if re.search(pattern, statement, re.IGNORECASE):
            return False
    
    return True


@dp.message(F.text)
async def echo(message: Message):    
    user_id = message.from_user.id
    user_query = message.text.strip()
    logger.info(f"Получен запрос от {user_id}: {user_query}")
    
    generator = SqlQueryGenerator(api_key=OPENROUTER_API_KEY)
    
    try:
        sql_query = await generator.generate_query(user_query = user_query)
        logger.info(f"Сгенерирован SQL для {user_id}: {sql_query}")
    except Exception as e:
        logger.error(f"Ошибка генерации SQL для {user_id}: {e}")
        await message.answer("0")
        return
    
    if not is_safe_sql(sql_query):
        logger.warning(f"Небезопасный SQL от {user_id}: {sql_query}")
        await message.answer("0")
        return

    try:
        async with get_db_session() as session:
            result = await get_result(session, sql_query)
    except Exception as e:
        logger.error(f"Ошибка БД для {user_id}: {e}")
        await message.answer("0")
        return
    
    logger.info(f"Отправлен ответ {user_id}: {result}")
    await message.answer(result)

async def main():   
    logger.info("=== ЗАПУСК БОТА ===")
    await init_db()
    
    try:
        logger.info("Бот запущен, ожидаем сообщения...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if engine:
            logger.info("Закрываем соединения с БД...")
            await engine.dispose()
        logger.info("=== БОТ ОСТАНОВЛЕН ===")

if __name__ == "__main__":
    asyncio.run(main())