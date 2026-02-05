import asyncio
import sys
import os
from dotenv import load_dotenv
from database import drop_and_create_tables, load_json_to_db
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('setup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def main():
    if len(sys.argv) != 2:
        logger.error("Использование: python setup_database.py <путь_к_json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    if not os.path.exists(json_path):
        logger.error(f"Файл {json_path} не найден")
        sys.exit(1)
    
    try:
        logger.info("Начинаем настройку базы данных...")
        
        await drop_and_create_tables()        
        await load_json_to_db(json_path)
        
        logger.info("База данных успешно настроена и загружена!")
        logger.info("Для запуска бота выполните: python bot.py")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())