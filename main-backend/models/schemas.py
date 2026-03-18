# =============================================
# VimaClip - Backend Principal
# Modelos de Dados (SQLModel)
# =============================================

from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, JSON, Column

class VideoBase(SQLModel):
    title: str
    url: str
    duration: float
    resolution: str
    engine_job_id: str
    clips_count: Optional[int] = 0

class Video(VideoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relacionamento com os clips gerados
    clips: List["Clip"] = Relationship(back_populates="video")

class ClipBase(SQLModel):
    start_time: str
    end_time: str
    format: str  # vertical, square, horizontal
    video_path: str # Caminho local no static server
    clip_model: Optional[str] = "auto"
    genre: Optional[str] = "auto"
    subtitle_style: Optional[str] = "karaoke"
    
class Clip(ClipBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Transcrição completa armazenada como JSON
    transcription: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    video: Video = Relationship(back_populates="clips")

# Schemas para API
class VideoCreate(VideoBase):
    pass

class ClipCreate(ClipBase):
    video_id: int
    transcription: Optional[dict] = None
