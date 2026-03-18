# =============================================
# VimaClip - Motor de Vídeo
# Serviço de Download de Vídeos (yt-dlp)
# =============================================
# Este módulo é responsável por baixar vídeos do YouTube
# e de outras plataformas suportadas pelo yt-dlp.
# =============================================

import os
import uuid
import logging
from typing import Dict, Any

import yt_dlp

# Configura o logger para este módulo
logger = logging.getLogger(__name__)


def download_video(url: str, output_dir: str) -> Dict[str, Any]:
    """
    Baixa um vídeo do YouTube (ou outra plataforma) usando yt-dlp.

    Parâmetros:
        url (str): URL completa do vídeo (ex: "https://youtube.com/watch?v=...")
        output_dir (str): Diretório onde o vídeo será salvo

    Retorna:
        dict: Dicionário com informações do download:
            - "video_path": caminho completo do arquivo baixado
            - "title": título do vídeo
            - "duration": duração em segundos
            - "resolution": resolução do vídeo (ex: "1920x1080")

    Exceções:
        Exception: Se o download falhar por qualquer motivo
                   (URL inválida, vídeo privado, rede, etc.)
    """

    # Gera um nome único para evitar conflitos entre downloads simultâneos
    unique_id = str(uuid.uuid4())[:8]

    # Garante que o diretório de saída existe
    os.makedirs(output_dir, exist_ok=True)

    # Template do nome do arquivo de saída
    output_template = os.path.join(output_dir, f"{unique_id}_%(title)s.%(ext)s")

    logger.info(f"Iniciando download do vídeo: {url}")

    try:
        # =============================================
        # PASSO 1: EXTRAIR METADADOS (sem filtrar formato)
        # Usamos configurações mínimas só para pegar título e duração
        # =============================================
        info_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get("title", "video_sem_titulo")
            video_duration = info_dict.get("duration", 0)
            video_width = info_dict.get("width", 0)
            video_height = info_dict.get("height", 0)

        logger.info(f"Título: {video_title}")
        logger.info(f"Duração: {video_duration} segundos")

        # =============================================
        # PASSO 2: BAIXAR O VÍDEO (com fallback de formatos)
        # Tenta vários formatos em ordem de preferência.
        # Se o primeiro falhar, tenta o próximo.
        # =============================================
        format_options = [
            "bestvideo+bestaudio/best",           # Ideal: melhor qualidade
            "bestvideo[height<=1080]+bestaudio",   # Fallback: limita resolução
            "best",                                # Último recurso: pré-combinado
        ]

        download_success = False
        last_error = None

        for fmt in format_options:
            try:
                logger.info(f"Tentando formato: {fmt}")

                ydl_opts = {
                    "outtmpl": output_template,
                    "format": fmt,
                    "merge_output_format": "mp4",
                    "quiet": True,
                    "no_warnings": True,
                    "postprocessors": [{
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4",
                    }],
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                download_success = True
                logger.info(f"Download concluído com formato: {fmt}")
                break

            except yt_dlp.utils.DownloadError as e:
                last_error = str(e)
                logger.warning(f"Formato '{fmt}' não disponível, tentando próximo...")
                continue

        if not download_success:
            raise Exception(
                f"Nenhum formato de vídeo disponível para esta URL. "
                f"Último erro: {last_error}"
            )

        # Procura o arquivo baixado pelo prefixo UUID
        video_path = _find_downloaded_file(output_dir, unique_id)

        if not video_path:
            raise FileNotFoundError(
                f"Arquivo baixado não encontrado no diretório: {output_dir}"
            )

        logger.info(f"Download concluído: {video_path}")

        return {
            "video_path": video_path,
            "title": video_title,
            "duration": video_duration,
            "resolution": f"{video_width}x{video_height}" if video_width else "desconhecida",
        }

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Erro no download do vídeo: {str(e)}")
        raise Exception(f"Falha ao baixar o vídeo: {str(e)}")

    except Exception as e:
        logger.error(f"Erro inesperado no download: {str(e)}")
        raise


def _find_downloaded_file(directory: str, prefix: str) -> str | None:
    """
    Procura o arquivo baixado pelo yt-dlp no diretório de saída.

    O yt-dlp pode gerar nomes diferentes do template (por causa de
    caracteres especiais no título), então procuramos pelo prefixo UUID.

    Parâmetros:
        directory (str): Diretório onde procurar
        prefix (str): Prefixo do UUID usado no download

    Retorna:
        str | None: Caminho completo do arquivo encontrado, ou None
    """
    for filename in os.listdir(directory):
        if filename.startswith(prefix):
            return os.path.join(directory, filename)
    return None
