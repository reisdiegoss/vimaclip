# =============================================
# VimaClip - Backend Principal
# Servidor Principal de Orquestração
# =============================================

import os
import logging
import shutil
import httpx
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from pydantic import BaseModel

from database import create_db_and_tables, get_session
from models.schemas import Video, Clip, VideoCreate

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações do Ambiente
VIDEO_ENGINE_URL = os.getenv("VIDEO_ENGINE_URL", "http://localhost:8000")
STATIC_DIR = os.getenv("STATIC_DIR", "./static")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs("./db", exist_ok=True)

app = FastAPI(
    title="VimaClip - Backend Principal",
    description="API de orquestração para edição de vídeos curtos.",
    version="1.0.0"
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos (clips gerados)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("Banco de dados inicializado.")

# --- Schemas de Requisição ---
class ProcessRequest(BaseModel):
    video_url: str
    segments: List[dict] # [{"start": "MM:SS", "end": "MM:SS"}]
    format: str = "vertical"
    burn_subtitles: bool = False
    subtitle_style: str = "karaoke"
    clip_model: str = "auto"
    genre: str = "auto"
    ai_instructions: str = ""

# --- Rotas da API ---

@app.get("/")
def health_check():
    return {"status": "online", "engine_api": VIDEO_ENGINE_URL}

@app.post("/api/videos/process")
async def process_video(
    request: ProcessRequest, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Inicia o processamento de um vídeo.
    Envia a requisição para o Motor de Vídeo (Docker).
    """
    logger.info(f"Recebida requisição para processar vídeo: {request.video_url}")
    
    # Payload para o motor
    payload = {
        "video_url": request.video_url,
        "segments": request.segments,
        "format": request.format,
        "layout": "single",
        "burn_subtitles": request.burn_subtitles,
        "subtitle_style": request.subtitle_style,
        "clip_model": request.clip_model,
        "genre": request.genre,
        "ai_instructions": request.ai_instructions
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VIDEO_ENGINE_URL}/api/engine/cut",
                json=payload,
                timeout=600.0  # Timeouts longos para processamento de vídeo
            )
            
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Motor de Vídeo retornou erro: {response.text}"
            )
            
        engine_data = response.json()
        
        # Salva o vídeo no banco de dados local
        metadata = engine_data["metadata"]
        db_video = Video(
            title=metadata["title"],
            url=request.video_url,
            duration=metadata["duration"],
            resolution=metadata["resolution"],
            engine_job_id=metadata["job_id"],
            clips_count=len(engine_data["segments"])
        )
        session.add(db_video)
        session.commit()
        session.refresh(db_video)
        
        # Processa e salva os clips gerados
        for i, seg_res in enumerate(engine_data["segments"]):
            # Em um sistema real, moveríamos o arquivo do Docker volume para o static
            # Como estamos no mesmo host (Windows), podemos tentar copiar via path
            
            # Converte path interno do Docker para path real do host
            # Priorizamos o path do vídeo cropado se existir
            docker_path = seg_res.get("cropped_path") or seg_res.get("output_path")
            host_path = docker_path.replace("/app/temp_videos", "../video-engine/temp_videos")
            
            # Gera nome do arquivo local
            file_extension = os.path.splitext(host_path)[1]
            local_filename = f"clip_{db_video.id}_{i}{file_extension}"
            local_dest_path = os.path.join(STATIC_DIR, local_filename)
            
            # Copia o arquivo para a pasta estática
            if os.path.exists(host_path):
                shutil.copy2(host_path, local_dest_path)
                logger.info(f"Clip copiado para: {local_dest_path}")
            else:
                logger.warning(f"Arquivo não encontrado para copiar: {host_path}")
            
            # Salva o clip no banco. A transcrição vem na raiz da resposta do motor
            db_clip = Clip(
                video_id=db_video.id,
                start_time=request.segments[i]["start"],
                end_time=request.segments[i]["end"] if request.segments else "auto",
                format=request.format,
                video_path=f"/static/{local_filename}",
                clip_model=request.clip_model,
                genre=request.genre,
                subtitle_style=request.subtitle_style,
                transcription=engine_data.get("transcription")
            )
            session.add(db_clip)
            
        session.commit()
        
        return {
            "message": "Vídeo processado e clips gerados com sucesso!",
            "video_id": db_video.id,
            "clips_count": len(engine_data["segments"])
        }

    except Exception as e:
        logger.error(f"Erro na orquestração: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos", response_model=List[Video])
def list_videos(session: Session = Depends(get_session)):
    return session.exec(select(Video)).all()

@app.get("/api/videos/{video_id}")
def get_video_details(video_id: int, session: Session = Depends(get_session)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    
    return {
        "video": video,
        "clips": video.clips
    }

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, session: Session = Depends(get_session)):
    """Deleta um vídeo, seus clips e os arquivos físicos correspondentes."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    try:
        # 1. Limpar arquivos dos clips no static/
        for clip in video.clips:
            clip_filename = os.path.basename(clip.video_path)
            clip_full_path = os.path.join(STATIC_DIR, clip_filename)
            if os.path.exists(clip_full_path):
                os.remove(clip_full_path)
                logger.info(f"Arquivo deletado: {clip_full_path}")

        # 2. Limpar pasta do job no motor (temp_videos)
        job_dir = f"../video-engine/temp_videos/job_{video.engine_job_id}"
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
            logger.info(f"Pasta de processamento deletada: {job_dir}")

        # 3. Remover do Banco de Dados
        session.delete(video)
        session.commit()
        
        return {"message": "Vídeo e arquivos deletados com sucesso!"}
    except Exception as e:
        logger.error(f"Erro ao deletar vídeo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/videos")
def delete_all_videos(session: Session = Depends(get_session)):
    """Limpa todo o histórico e todos os arquivos físicos."""
    videos = session.exec(select(Video)).all()
    for video in videos:
        delete_video(video.id, session)
    return {"message": "Todo o histórico foi limpo com sucesso!"}
