# =============================================
# VimaClip - Motor de Vídeo
# Serviço de Corte de Vídeos (FFmpeg)
# =============================================
# Este módulo usa o FFmpeg (via subprocess) para cortar
# trechos específicos de um vídeo baseado em timestamps.
# =============================================

import os
import subprocess
import logging
from typing import List, Dict, Any

# Configura o logger para este módulo
logger = logging.getLogger(__name__)


def timestamp_to_seconds(timestamp: str) -> float:
    """
    Converte um timestamp no formato "MM:SS" ou "HH:MM:SS" para segundos.

    Exemplos:
        "01:30" -> 90.0
        "02:45" -> 165.0
        "01:02:30" -> 3750.0

    Parâmetros:
        timestamp (str): Timestamp no formato "MM:SS" ou "HH:MM:SS"

    Retorna:
        float: Tempo total em segundos

    Exceções:
        ValueError: Se o formato do timestamp for inválido
    """
    parts = timestamp.strip().split(":")

    if len(parts) == 2:
        # Formato MM:SS
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)

    elif len(parts) == 3:
        # Formato HH:MM:SS
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

    else:
        raise ValueError(
            f"Formato de timestamp inválido: '{timestamp}'. "
            f"Use 'MM:SS' ou 'HH:MM:SS'."
        )


def seconds_to_timestamp(seconds: float) -> str:
    """
    Converte segundos para o formato "HH:MM:SS.mmm" usado pelo FFmpeg.

    Exemplos:
        90.0 -> "00:01:30.000"
        165.5 -> "00:02:45.500"

    Parâmetros:
        seconds (float): Tempo em segundos

    Retorna:
        str: Timestamp no formato "HH:MM:SS.mmm"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def cut_video_segments(
    video_path: str,
    segments: List[Dict[str, str]],
    output_dir: str
) -> List[Dict[str, Any]]:
    """
    Corta um vídeo em múltiplos segmentos usando o FFmpeg.

    Para cada segmento da lista, o FFmpeg extrai o trecho correspondente
    do vídeo original e salva como um novo arquivo MP4.

    Parâmetros:
        video_path (str): Caminho completo do vídeo original
        segments (list): Lista de dicionários com "start" e "end"
                         Exemplo: [{"start": "01:20", "end": "02:45"}]
        output_dir (str): Diretório onde os arquivos cortados serão salvos

    Retorna:
        list: Lista de dicionários com informações de cada segmento cortado:
            - "segment_index": índice do segmento (0, 1, 2...)
            - "start": timestamp original de início
            - "end": timestamp original de fim
            - "output_path": caminho do arquivo de saída
            - "duration": duração do segmento em segundos

    Exceções:
        Exception: Se o FFmpeg falhar no corte de algum segmento
    """

    # Garante que o diretório de saída existe
    os.makedirs(output_dir, exist_ok=True)

    # Verifica se o arquivo de entrada existe
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Vídeo original não encontrado: {video_path}")

    # Lista para armazenar os resultados de cada segmento
    results = []

    # Pega o nome base do arquivo original (sem extensão)
    base_name = os.path.splitext(os.path.basename(video_path))[0]

    for index, segment in enumerate(segments):
        start_str = segment["start"]
        end_str = segment["end"]

        # Converte os timestamps para segundos (internamente)
        start_seconds = timestamp_to_seconds(start_str)
        end_seconds = timestamp_to_seconds(end_str)

        # Calcula a duração do segmento
        duration = end_seconds - start_seconds

        # Valida que o fim é depois do início
        if duration <= 0:
            raise ValueError(
                f"Segmento {index}: o tempo de fim ({end_str}) "
                f"deve ser maior que o tempo de início ({start_str})."
            )

        # Monta o nome do arquivo de saída
        output_filename = f"{base_name}_seg{index:02d}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        # =============================================
        # COMANDO FFMPEG PARA CORTE
        # =============================================
        # -i: arquivo de entrada
        # -ss: ponto de início (posicionar antes de -i é mais rápido,
        #       mas pode ser impreciso; após -i é preciso mas mais lento)
        # -to: ponto de fim (relativo ao início do arquivo original)
        # -c copy: copia os streams sem re-encodar (MUITO mais rápido)
        # -avoid_negative_ts make_zero: evita timestamps negativos
        # -y: sobrescreve o arquivo de saída se já existir
        # =============================================
        ffmpeg_command = [
            "ffmpeg",
            "-i", video_path,               # Arquivo de entrada
            "-ss", seconds_to_timestamp(start_seconds),  # Início do corte
            "-to", seconds_to_timestamp(end_seconds),    # Fim do corte
            "-c", "copy",                    # Sem re-encoding (rápido!)
            "-avoid_negative_ts", "make_zero",  # Corrige timestamps
            "-y",                            # Sobrescreve se existir
            output_path                      # Arquivo de saída
        ]

        logger.info(
            f"Cortando segmento {index}: "
            f"{start_str} -> {end_str} ({duration:.1f}s)"
        )
        logger.debug(f"Comando FFmpeg: {' '.join(ffmpeg_command)}")

        try:
            # Executa o FFmpeg como subprocesso
            result = subprocess.run(
                ffmpeg_command,
                capture_output=True,  # Captura stdout e stderr
                text=True,            # Decodifica saída como texto
                check=True            # Levanta exceção se retornar erro
            )

            # Verifica se o arquivo de saída foi criado com sucesso
            if not os.path.exists(output_path):
                raise FileNotFoundError(
                    f"FFmpeg executou mas o arquivo de saída não foi criado: "
                    f"{output_path}"
                )

            # Pega o tamanho do arquivo gerado (em bytes)
            file_size = os.path.getsize(output_path)

            logger.info(
                f"Segmento {index} cortado com sucesso: "
                f"{output_path} ({file_size / 1024 / 1024:.1f} MB)"
            )

            # Adiciona o resultado à lista
            results.append({
                "segment_index": index,
                "start": start_str,
                "end": end_str,
                "output_path": output_path,
                "duration": duration,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
            })

        except subprocess.CalledProcessError as e:
            # O FFmpeg retornou um código de erro
            logger.error(
                f"FFmpeg falhou no segmento {index}: {e.stderr}"
            )
            raise Exception(
                f"Erro ao cortar segmento {index} ({start_str}-{end_str}): "
                f"{e.stderr}"
            )

    logger.info(f"Todos os {len(results)} segmentos foram cortados com sucesso!")
    return results
