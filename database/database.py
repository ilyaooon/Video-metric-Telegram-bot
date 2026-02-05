import aiofiles
import os
import json
from datetime import datetime
import uuid
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base, Video, VideoSnapshot
import logging
import sys

logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL не установлен в .env файле")
    sys.exit(1)

async def drop_and_create_tables():
    logger.info("Удаляем существующие таблицы...")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10
    )
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS video_snapshots CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS videos CASCADE"))
        logger.info("Таблицы удалены")
        
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы созданы заново")
    
    return engine

async def load_json_to_db(json_path: str):
    logger.info(f"Загружаем данные из {json_path}...")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20
    )
    
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )   

    async with aiofiles.open(json_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        data = json.loads(content)

    videos_count = 0
    snapshots_count = 0
    total_videos = len(data['videos'])
    
    logger.info(f"Найдено {total_videos} видео для загрузки")
    
    try:
        async with async_session() as session:
            batch_size = 100
            video_batch = []
            snapshot_batch = []
            
            for i, video_data in enumerate(data['videos'], 1):
                video = Video(
                    id=uuid.UUID(video_data['id']),
                    creator_id=str(video_data['creator_id']), 
                    video_created_at=datetime.fromisoformat(video_data['video_created_at'].replace('Z', '+00:00')),
                    views_count=video_data['views_count'],
                    likes_count=video_data['likes_count'],
                    comments_count=video_data['comments_count'],
                    reports_count=video_data['reports_count'],
                    created_at=datetime.fromisoformat(video_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(video_data['updated_at'].replace('Z', '+00:00'))
                )
                video_batch.append(video)
                videos_count += 1                
                
                snapshots = video_data.get('snapshots', [])
                for snapshot in snapshots:
                    snapshot_obj = VideoSnapshot(
                        id=str(snapshot['id']),  
                        video_id=uuid.UUID(video_data['id']),
                        views_count=snapshot['views_count'],
                        likes_count=snapshot['likes_count'],
                        comments_count=snapshot['comments_count'],
                        reports_count=snapshot['reports_count'],
                        delta_views_count=snapshot['delta_views_count'],
                        delta_likes_count=snapshot['delta_likes_count'],
                        delta_comments_count=snapshot['delta_comments_count'],
                        delta_reports_count=snapshot['delta_reports_count'],
                        created_at=datetime.fromisoformat(snapshot['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(snapshot['updated_at'].replace('Z', '+00:00'))
                    )
                    snapshot_batch.append(snapshot_obj)
                    snapshots_count += 1
                
                if len(video_batch) >= batch_size:
                    session.add_all(video_batch)
                    session.add_all(snapshot_batch)
                    await session.commit()
                    video_batch = []
                    snapshot_batch = []
                    
                    progress = int(i / total_videos * 100)
                    if i % 500 == 0 or i == total_videos:
                        logger.info(f"Загружено {i}/{total_videos} видео ({progress}%)")
            
            if video_batch:
                session.add_all(video_batch)
                session.add_all(snapshot_batch)
                await session.commit()
            
            logger.info(f"Загрузка завершена! Видео: {videos_count}, Снапшотов: {snapshots_count}")
            
            result = await session.execute(text("SELECT COUNT(*) FROM videos"))
            video_count_db = result.scalar()
            
            result = await session.execute(text("SELECT COUNT(*) FROM video_snapshots"))
            snapshot_count_db = result.scalar()
            
            logger.info(f"Проверка: {video_count_db} видео, {snapshot_count_db} снапшотов в БД")
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()
        logger.info("Соединение с БД закрыто")