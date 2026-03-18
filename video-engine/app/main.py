# =============================================
# VimaClip - Motor de Vídeo
# Arquivo Principal da API (FastAPI)
# =============================================
# Este é o ponto de entrada do microsserviço.
# Ele define as rotas da API e orquestra o pipeline
# de processamento de vídeo.
#
# Para rodar:
#   docker-compose up --build
#
# A documentação interativa (Swagger) fica em:
#   http://localhost:8000/docs
# =============================================

import os
import uuid
import shutil
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Importa os schemas (modelos de dados)
from app.models.schemas import (
    CutRequest,
    CutResponse,
    SegmentResult,
    TranscriptionResult,
    TranscriptionWord,
)

# Importa os serviços do pipeline
from app.services.downloader import download_video
from app.services.cutter import cut_video_segments
from app.services.transcriber import transcribe_audio_with_groq, get_semantic_segments, generate_ass_file
from app.services.cropper import apply_smart_crop

# =============================================
# CONFIGURAÇÕES INICIAIS
# =============================================

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configura o sistema de logs
# Nível DEBUG mostra TUDO (útil para desenvolvimento)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vimaclip")

# Diretório temporário para vídeos (configurável via .env)
TEMP_DIR = os.getenv("TEMP_DIR", "/app/temp_videos")

# =============================================
# CRIAÇÃO DA APLICAÇÃO FASTAPI
# =============================================

app = FastAPI(
    title="VimaClip - Motor de Vídeo",
    description=(
        "API de processamento de vídeos curtos. "
        "Realiza download, corte, crop e transcrição de vídeos. "
        "Roda dentro de um container Docker como microsserviço."
    ),
    version="1.0.0",
    docs_url="/docs",         # Swagger UI
    redoc_url="/redoc",       # ReDoc (documentação alternativa)
)

# =============================================
# CONFIGURAÇÃO DE CORS
# =============================================
# Permite que o Frontend (que roda FORA do Docker)
# acesse esta API sem ser bloqueado pelo navegador.
# Em produção, substitua o "*" pelos domínios reais.
# =============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Aceita requisições de qualquer origem
    allow_credentials=True,       # Permite cookies/auth headers
    allow_methods=["*"],          # Aceita todos os métodos HTTP
    allow_headers=["*"],          # Aceita todos os headers
)


# =============================================
# ROTA: HEALTH CHECK
# =============================================
# Rota simples para verificar se a API está no ar.
# Usada pelo Docker, load balancers e monitoramento.
# =============================================

@app.get(
    "/",
    summary="Health Check",
    description="Verifica se o Motor de Vídeo está rodando corretamente.",
    tags=["Sistema"],
)
async def health_check():
    """
    Retorna o status da API e informações básicas do sistema.

    Útil para:
    - Verificar se o container está no ar
    - Testar a conexão entre o frontend/backend e o motor
    - Monitoramento de saúde do serviço
    """
    return {
        "status": "online",
        "service": "VimaClip Motor de Vídeo",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "temp_dir": TEMP_DIR,
        "temp_dir_exists": os.path.exists(TEMP_DIR),
    }


# =============================================
# ROTA PRINCIPAL: /api/engine/cut
# =============================================
# Esta é a rota que recebe o pedido de edição
# e executa todo o pipeline de processamento.
#
# Pipeline:
#   1. Download do vídeo (yt-dlp)
#   2. Corte dos segmentos (FFmpeg)
#   3. Transcrição do áudio (mock Groq)
#   4. Smart Crop (mock MediaPipe + FFmpeg)
# =============================================

@app.post(
    "/api/engine/cut",
    response_model=CutResponse,
    summary="Processar e cortar vídeo",
    description=(
        "Recebe uma URL de vídeo, baixa, corta nos segmentos especificados, "
        "transcreve o áudio e aplica crop inteligente baseado no formato."
    ),
    tags=["Processamento"],
)
async def cut_video(request: CutRequest):
    """
    Rota principal do Motor de Vídeo.

    Recebe um JSON com a URL do vídeo, formato desejado,
    layout e lista de segmentos para cortar.

    O processamento segue 4 etapas:
        A) Download do vídeo com yt-dlp
        B) Corte dos segmentos com FFmpeg
        C) Transcrição do áudio (mock Groq/Whisper)
        D) Aplicação de Smart Crop (mock MediaPipe)

    Parâmetros (via JSON no body):
        video_url (str): URL do YouTube ou plataforma suportada
        format (str): "vertical", "horizontal" ou "square"
        layout (str): "single", "split" ou "pip"
        segments (list): Lista de {"start": "MM:SS", "end": "MM:SS"}

    Retorna:
        CutResponse: Status, caminhos dos arquivos e transcrição

    Erros:
        422: JSON inválido / campos obrigatórios ausentes
        500: Erro interno no processamento
    """

    # Gera um ID único para esta requisição de processamento
    # Isso isola os arquivos de cada requisição em sua própria pasta
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(TEMP_DIR, f"job_{job_id}")

    logger.info("=" * 60)
    logger.info(f"NOVO JOB: {job_id}")
    logger.info(f"URL: {request.video_url}")
    logger.info(f"Formato: {request.format.value}")
    logger.info(f"Layout: {request.layout.value}")
    logger.info(f"Segmentos: {len(request.segments)}")
    logger.info("=" * 60)

    try:
        # Cria o diretório do job
        os.makedirs(job_dir, exist_ok=True)

        # =============================================
        # ETAPA A: DOWNLOAD DO VÍDEO
        # =============================================
        logger.info("[ETAPA A] Iniciando download do vídeo...")

        download_result = download_video(
            url=request.video_url,
            output_dir=job_dir,
        )

        video_path = download_result["video_path"]
        logger.info(f"[ETAPA A] Download concluído: {video_path}")

        # =============================================
        # ETAPA B (NOVA): CLIPPING INTELIGENTE (IA)
        # =============================================
        if request.ai_instructions and not request.segments:
            logger.info("[IA] Iniciando Clipping Semântico...")
            # Transcreve o vídeo original INTEGRAL para a IA analisar
            full_transcription = transcribe_audio_with_groq(video_path)
            
            # Pede para a IA sugerir os melhores trechos
            ai_segments = get_semantic_segments(full_transcription["text"], request.ai_instructions)
            
            if ai_segments:
                logger.info(f"[IA] IA sugeriu {len(ai_segments)} trechos: {ai_segments}")
                # Atualiza a request com os segmentos da IA
                from app.models.schemas import SegmentModel
                request.segments = [SegmentModel(**s) for s in ai_segments]
            else:
                logger.warning("[IA] IA não retornou trechos. Usando fallback de 30s iniciais.")
                from app.models.schemas import SegmentModel
                request.segments = [SegmentModel(start="00:00", end="00:30")]

        # =============================================
        # ETAPA B: CORTE DOS SEGMENTOS
        # =============================================
        logger.info("[ETAPA B] Iniciando corte dos segmentos...")

        # Converte os objetos Pydantic para dicts simples
        segments_data = [
            {"start": seg.start, "end": seg.end}
            for seg in request.segments
        ]

        cut_results = cut_video_segments(
            video_path=video_path,
            segments=segments_data,
            output_dir=job_dir,
        )

        logger.info(f"[ETAPA B] {len(cut_results)} segmento(s) cortado(s)")

        # =============================================
        # ETAPA C/D: TRANSCRIÇÃO E SMART CROP (POR SEGMENTO)
        # =============================================
        logger.info("[ETAPA C/D] Iniciando transcrição e crop dos segmentos...")

        segment_results = []
        main_transcription = {"text": "", "language": "pt", "words": [], "srt_path": None}
        
        for cut_result in cut_results:
            seg_path = cut_result["output_path"]
            
            # 1. Transcrever o segmento atual para ter o timestamp correto
            transcription_data = transcribe_audio_with_groq(seg_path)
            srt_path = transcription_data.get("srt_path")

            # 1b. Se for estilo Karaokê, gerar o arquivo ASS necessário
            if request.subtitle_style.value == "karaoke":
                ass_path = srt_path.replace(".srt", ".ass")
                generate_ass_file(transcription_data["words"], ass_path)

            # 2. Aplicar o crop (com burn-in opcional)
            cropped_path = apply_smart_crop(
                video_path=seg_path,
                format=request.format.value,
                layout=request.layout.value,
                burn_subtitles=request.burn_subtitles,
                srt_path=srt_path,
                output_dir=job_dir,
                subtitle_style=request.subtitle_style.value
            )

            segment_results.append(
                SegmentResult(
                    segment_index=cut_result["segment_index"],
                    start=cut_result["start"],
                    end=cut_result["end"],
                    output_path=seg_path,
                    cropped_path=cropped_path,
                )
            )
            
            # Se for o primeiro segmento, usamos ele como referência para a resposta global (compatibilidade)
            if cut_result["segment_index"] == 0:
                main_transcription = transcription_data

        logger.info(f"[FIM] {len(segment_results)} segmento(s) processados com sucesso")

        # =============================================
        # MONTAGEM DA RESPOSTA
        # =============================================

        # Converte a transcrição do primeiro segmento para o modelo Pydantic
        transcription_result = TranscriptionResult(
            text=main_transcription["text"],
            language=main_transcription["language"],
            words=[
                TranscriptionWord(**word)
                for word in main_transcription["words"]
            ],
        )

        # Monta a resposta final
        response = CutResponse(
            status="success",
            message=(
                f"Vídeo processado com sucesso! "
                f"{len(segment_results)} segmento(s) gerado(s)."
            ),
            original_video=video_path,
            segments=segment_results,
            transcription=transcription_result,
            metadata={
                "job_id": job_id,
                "title": download_result.get("title", ""),
                "duration": download_result.get("duration", 0),
                "resolution": download_result.get("resolution", ""),
                "format": request.format.value,
                "layout": request.layout.value,
                "processed_at": datetime.now().isoformat(),
            },
        )

        logger.info("=" * 60)
        logger.info(f"JOB {job_id} CONCLUÍDO COM SUCESSO!")
        logger.info("=" * 60)

        return response

    except FileNotFoundError as e:
        # Arquivo não encontrado (download falhou)
        logger.error(f"Arquivo não encontrado: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo não encontrado: {str(e)}",
        )

    except ValueError as e:
        # Dados inválidos (timestamps ruins, formato errado)
        logger.error(f"Dados inválidos: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Dados inválidos: {str(e)}",
        )

    except Exception as e:
        # Qualquer outro erro
        logger.error(f"Erro no processamento do job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno no processamento: {str(e)}",
        )


# =============================================
# ROTA: LIMPEZA DE ARQUIVOS TEMPORÁRIOS
# =============================================
# Rota auxiliar para limpar os arquivos gerados.
# Importante para não encher o disco do servidor.
# =============================================

@app.delete(
    "/api/engine/cleanup/{job_id}",
    summary="Limpar arquivos temporários de um job",
    description="Remove todos os arquivos gerados por um job específico.",
    tags=["Sistema"],
)
async def cleanup_job(job_id: str):
    """
    Remove todos os arquivos temporários de um job específico.

    Parâmetros:
        job_id (str): ID do job retornado na resposta do /api/engine/cut

    Retorna:
        dict: Status da limpeza
    """
    job_dir = os.path.join(TEMP_DIR, f"job_{job_id}")

    if not os.path.exists(job_dir):
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' não encontrado.",
        )

    try:
        # Remove a pasta inteira do job e todos os seus arquivos
        shutil.rmtree(job_dir)
        logger.info(f"Arquivos do job {job_id} removidos com sucesso")

        return {
            "status": "success",
            "message": f"Arquivos do job '{job_id}' removidos com sucesso.",
        }

    except Exception as e:
        logger.error(f"Erro ao limpar job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao limpar arquivos: {str(e)}",
        )


# =============================================
# ROTA: LISTAR JOBS ATIVOS
# =============================================

@app.get(
    "/api/engine/jobs",
    summary="Listar jobs ativos",
    description="Lista todos os jobs com arquivos temporários no servidor.",
    tags=["Sistema"],
)
async def list_jobs():
    """
    Lista todos os diretórios de jobs existentes no TEMP_DIR.
    Útil para depuração e monitoramento.
    """
    if not os.path.exists(TEMP_DIR):
        return {"jobs": [], "total": 0}

    jobs = []
    for dirname in os.listdir(TEMP_DIR):
        if dirname.startswith("job_"):
            job_path = os.path.join(TEMP_DIR, dirname)
            if os.path.isdir(job_path):
                # Conta os arquivos dentro do job
                files = os.listdir(job_path)
                # Calcula o tamanho total dos arquivos
                total_size = sum(
                    os.path.getsize(os.path.join(job_path, f))
                    for f in files
                    if os.path.isfile(os.path.join(job_path, f))
                )

                jobs.append({
                    "job_id": dirname.replace("job_", ""),
                    "files_count": len(files),
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                })

    return {
        "jobs": jobs,
        "total": len(jobs),
    }
