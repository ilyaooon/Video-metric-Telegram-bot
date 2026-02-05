from sqlalchemy import Column, BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(String)
    video_created_at = Column(DateTime(timezone=True))
    views_count = Column(BigInteger)
    likes_count = Column(BigInteger)
    comments_count = Column(BigInteger)
    reports_count = Column(BigInteger)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

class VideoSnapshot(Base):
    __tablename__ = 'video_snapshots'
    
    id = Column(String, primary_key=True) 
    video_id = Column(UUID(as_uuid=True))
    views_count = Column(BigInteger)
    likes_count = Column(BigInteger)
    comments_count = Column(BigInteger)
    reports_count = Column(BigInteger)
    delta_views_count = Column(BigInteger)
    delta_likes_count = Column(BigInteger)
    delta_comments_count = Column(BigInteger)
    delta_reports_count = Column(BigInteger)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))