# =============================================
# VimaClip - Motor de Vídeo
# Serviço de Transcrição e Clipping Semântico (Groq)
# =============================================

import os
import logging
import subprocess
import requests
import datetime
import json
import re
from typing import Dict, Any, List

# Configura o logger
logger = logging.getLogger(__name__)

def transcribe_audio_with_groq(video_path: str) -> Dict[str, Any]:
    """Transcreve áudio via Groq Whisper API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY ausente. Usando transcrição simulada.")
        return _get_mock_transcription(video_path)

    output_dir = os.path.dirname(video_path)
    try:
        audio_path = _extract_audio(video_path, output_dir)
        raw_result = _send_to_groq(audio_path, api_key)
        formatted_result = _format_groq_response(raw_result)
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        generate_srt_file(formatted_result["words"], srt_path)
        formatted_result["srt_path"] = srt_path
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return formatted_result
    except Exception as e:
        logger.error(f"Erro Groq: {e}")
        return _get_mock_transcription(video_path)

def _extract_audio(video_path: str, output_dir: str) -> str:
    audio_path = os.path.join(output_dir, "temp_audio.mp3")
    cmd = ["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", "-y", audio_path]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path

def _send_to_groq(audio_path: str, api_key: str) -> dict:
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
        data = {
            "model": "whisper-large-v3",
            "language": "pt",
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
        }
        response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    return response.json()

def _format_groq_response(raw_result: dict) -> dict:
    words = [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in raw_result.get("words", [])]
    return {"text": raw_result.get("text", ""), "language": "pt", "words": words}

def get_semantic_segments(transcription_text: str, ai_instructions: str = "") -> List[Dict[str, str]]:
    """
    Usa o Groq (LLAMA3) para identificar os melhores momentos para clips.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return []

    prompt = f"""
    Analise a transcrição abaixo e identifique os momentos mais impactantes, virais ou informativos.
    Instruções adicionais do usuário: {ai_instructions if ai_instructions else "Nenhuma"}
    
    Retorne APENAS um JSON no formato: [{"start": "MM:SS", "end": "MM:SS", "reason": "motivo"}]
    Tente criar clips de 30 a 60 segundos.
    
    Transcrição:
    {transcription_text}
    """

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        # Extrair a lista do objeto JSON retornado pelo Groq
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "segments" in parsed:
            return parsed["segments"]
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception as e:
        logger.error(f"Erro no Clipping IA: {e}")
        return []

def generate_srt_file(words: List[dict], output_path: str):
    def fmt(s):
        td = datetime.timedelta(seconds=s)
        ts = int(td.total_seconds())
        ms = int((s - ts) * 1000)
        return f"{ts//3600:02d}:{(ts%3600)//60:02d}:{ts%60:02d},{ms:03d}"
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i in range(0, len(words), 5):
            chunk = words[i:i+5]
            f.write(f"{i//5 + 1}\n{fmt(chunk[0]['start'])} --> {fmt(chunk[-1]['end'])}\n{' '.join(w['word'] for w in chunk)}\n\n")

def generate_ass_file(words: List[dict], output_path: str):
    header = """[Script Info]
Title: VimaClip Dynamic Legend
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,1,0,2,10,10,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def fmt(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            for i in range(0, len(words), 8):
                chunk = words[i:i+8]
                f.write(f"Dialogue: 0,{fmt(float(chunk[0]['start']))},{fmt(float(chunk[-1]['end']))},Default,,0,0,0,,{' '.join(w['word'] for w in chunk)}\n")
    except Exception as e:
        logger.error(f"Erro ASS: {e}")

def _get_mock_transcription(video_path: str) -> dict:
    return {"text": "Transcrição simulada para VimaClip.", "words": [{"word": "VimaClip", "start": 0.0, "end": 2.0}]}
