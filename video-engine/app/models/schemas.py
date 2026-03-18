# =============================================
# VimaClip - Motor de Vídeo
# Schemas Pydantic (Modelos de dados da API)
# =============================================
# Este arquivo define a "forma" dos dados que a API aceita e retorna.
# O Pydantic valida automaticamente os dados recebidos,
# retornando erro 422 se algo estiver fora do formato.
# =============================================

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class VideoFormat(str, Enum):
    """
    Formatos de vídeo suportados.
    - vertical: 9:16 (Shorts, Reels, TikTok)
    - horizontal: 16:9 (YouTube padrão)
    - square: 1:1 (Instagram feed)
    """
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    SQUARE = "square"


class VideoLayout(str, Enum):
    """
    Layouts de composição do vídeo.
    - single: apenas o vídeo principal
    - split: tela dividida (futuro)
    - pip: picture-in-picture (futuro)
    """
    SINGLE = "single"
    SPLIT = "split"
    PIP = "pip"


class SubtitleStyle(str, Enum):
    """
    Estilos visuais de legendas para burn-in.
    """
    CLASSIC = "classic"
    KARAOKE = "karaoke"
    DEEP_DIVER = "deep_diver"
    POD_P = "pod_p"
    POPLINE = "popline"
    SEAMLESS_BOUNCE = "seamless_bounce"
    BEASTY = "beasty"
    YOUSHAEI = "youshaei"
    MOZI = "mozi"
    GLITCH_INFINITE = "glitch_infinite"
    BABY_EARTHQUAKE = "baby_earthquake"
    IMPACT_PRO = "impact_pro"
    MINIMAL = "minimal"


class SegmentModel(BaseModel):
    """
    Representa um trecho do vídeo a ser cortado.
    Exemplo: {"start": "01:20", "end": "02:45"}

    O formato aceito é "MM:SS" ou "HH:MM:SS".
    """
    start: str = Field(
        ...,
        description="Momento inicial do corte no formato MM:SS ou HH:MM:SS",
        examples=["01:20", "00:30"]
    )
    end: str = Field(
        ...,
        description="Momento final do corte no formato MM:SS ou HH:MM:SS",
        examples=["02:45", "01:00"]
    )


class CutRequest(BaseModel):
    """
    Corpo da requisição POST para /api/engine/cut.

    Este é o JSON que o frontend/backend principal envia
    para o Motor de Vídeo processar.
    """
    video_url: str = Field(
        ...,
        description="URL do vídeo no YouTube ou outra plataforma suportada pelo yt-dlp",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    )
    format: VideoFormat = Field(
        default=VideoFormat.VERTICAL,
        description="Formato de saída do vídeo (vertical, horizontal, square)"
    )
    layout: VideoLayout = Field(
        default=VideoLayout.SINGLE,
        description="Layout de composição (single, split, pip)"
    )
    burn_subtitles: bool = Field(
        default=False,
        description="Se verdadeiro, as legendas serão renderizadas diretamente no vídeo (Burn-in)"
    )
    subtitle_style: SubtitleStyle = Field(
        default=SubtitleStyle.KARAOKE,
        description="Estilo visual da legenda"
    )
    clip_model: str = Field(default="auto", description="Modelo de recorte IA")
    genre: str = Field(default="auto", description="Gênero do vídeo")
    ai_instructions: str = Field(default="", description="Instruções para a IA encontrar momentos")
    segments: List[SegmentModel] = Field(
        default_factory=list,
        description="Lista de trechos (opcional se ai_instructions for usado)"
    )


class TranscriptionWord(BaseModel):
    """
    Representa uma palavra individual na transcrição.
    Inclui timestamps para sincronização de legendas.
    """
    word: str = Field(..., description="A palavra transcrita")
    start: float = Field(..., description="Tempo de início em segundos")
    end: float = Field(..., description="Tempo de fim em segundos")


class TranscriptionResult(BaseModel):
    """
    Resultado da transcrição de áudio.
    Contém o texto completo e as palavras com timestamps.
    """
    text: str = Field(..., description="Texto completo da transcrição")
    language: str = Field(default="pt", description="Idioma detectado")
    words: List[TranscriptionWord] = Field(
        default_factory=list,
        description="Lista de palavras com timestamps"
    )


class SegmentResult(BaseModel):
    """
    Resultado do processamento de um segmento individual.
    """
    segment_index: int = Field(..., description="Índice do segmento (começando em 0)")
    start: str = Field(..., description="Timestamp de início original")
    end: str = Field(..., description="Timestamp de fim original")
    output_path: str = Field(..., description="Caminho do arquivo de saída")
    cropped_path: Optional[str] = Field(
        None,
        description="Caminho do arquivo cropado (após aplicar formato)"
    )


class CutResponse(BaseModel):
    """
    Resposta da rota /api/engine/cut.

    Contém o status do processamento, os caminhos dos arquivos gerados,
    a transcrição do áudio e metadados úteis.
    """
    status: str = Field(
        ...,
        description="Status do processamento: 'success' ou 'error'"
    )
    message: str = Field(
        ...,
        description="Mensagem descritiva do resultado"
    )
    original_video: Optional[str] = Field(
        None,
        description="Caminho do vídeo original baixado"
    )
    segments: List[SegmentResult] = Field(
        default_factory=list,
        description="Lista com os resultados de cada segmento processado"
    )
    transcription: Optional[TranscriptionResult] = Field(
        None,
        description="Resultado da transcrição do áudio (mock por enquanto)"
    )
    metadata: Optional[dict] = Field(
        None,
        description="Metadados extras (título do vídeo, duração, etc.)"
    )
