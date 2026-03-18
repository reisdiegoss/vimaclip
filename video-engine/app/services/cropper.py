# =============================================
# VimaClip - Motor de Vídeo
# Serviço de Smart Director Ultra (v7.0 - QUANTUM)
# =============================================
# Arquitetura: Frame Extraction + Center Exclusion + Low-Threshold Split
# Foco: Zero Bonecos, Zero Cortes em Locutor Lateral
# =============================================

import os
import subprocess
import cv2
import mediapipe as mp
import numpy as np
import logging
import uuid
import shutil
from typing import Optional, List, Dict, Any

# Configura o logger
logger = logging.getLogger(__name__)

# Inicializa o MediaPipe (Face Mesh para detecção ultra-precisa)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True, 
    max_num_faces=5,
    min_detection_confidence=0.5
)

# Constantes de Enquadramento
ASPECT_RATIOS = {
    "vertical": {"width_ratio": 9, "height_ratio": 16},
    "horizontal": {"width_ratio": 16, "height_ratio": 9},
    "square": {"width_ratio": 1, "height_ratio": 1},
}

# Índices do Face Mesh para lábios
LIP_INDEXES = [
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 42, 183, 78
]

def apply_smart_crop(
    video_path: str,
    output_dir: str,
    format: str = "vertical",
    layout: str = "auto",
    burn_subtitles: bool = False,
    srt_path: Optional[str] = None,
    subtitle_style: str = "classic"
) -> str:
    """
    Motor Smart Director v7.0 QUANTUM:
    - Extração via FFmpeg para garantir visão total (AV1 safe).
    - Centro-Inferior BLACKLIST: Mata bonecos no centro da mesa.
    - Low-Threshold Split: 5% de diálogo já ativa o modo Stacked.
    - Lateral Focus: Se um humano estiver na borda, o centro "puxa" pra ele.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_director_cut_{format}.mp4")

    iw, ih = _get_video_dims(video_path)
    ratio = ASPECT_RATIOS.get(format, ASPECT_RATIOS["vertical"])
    rw, rh = ratio["width_ratio"], ratio["height_ratio"]

    temp_frames_dir = os.path.join(output_dir, f"frames_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_frames_dir, exist_ok=True)

    try:
        logger.info("[SMART-DIRECTOR] Auditando frames com filtragem radial...")
        _extract_frames_ffmpeg_v7(video_path, temp_frames_dir)

        logger.info("[SMART-DIRECTOR] Calculando Quantum Timeline...")
        directors_log = _analyze_frames_v7(temp_frames_dir)
        
        if not directors_log:
            logger.warning("[SMART-DIRECTOR] Nenhuma face humana válida detectada.")
            final_center_x = 0.5
            multi_human_ratio = 0
        else:
            # Seleção Inteligente: Foca em quem falou MAIS no clip inteiro (mediana dos ativos)
            speaking_xs = [d["center_x"] for d in directors_log if d["speaking"]]
            if speaking_xs:
                final_center_x = float(np.median(speaking_xs))
            else:
                # Se ninguém falar, pega a mediana geral
                final_center_x = float(np.median([d["center_x"] for d in directors_log]))
            
            multi_human_ratio = sum(1 for d in directors_log if d["count"] >= 2) / len(directors_log)

        # STICKY CENTER (Zona de segurança 5% - mais responsivo agora)
        if abs(final_center_x - 0.5) < 0.05:
            final_center_x = 0.5

        # 1. DECISÃO DE SPLIT-SCREEN (QUANTUM THRESHOLD: 5%)
        # Se houver diálogo claro, forçamos o modo Stacked
        if layout == "auto" and format in ["vertical", "square"] and multi_human_ratio > 0.05:
            logger.info(f"[SMART-DIRECTOR] Tomada Aberta Detectada ({multi_human_ratio:.1%}) -> Ativando STACKED VIEW.")
            targets_split = _get_split_targets_v7(directors_log)
            return _execute_stacked_crop_v7(video_path, output_path, targets_split, iw, ih, format, burn_subtitles, srt_path)

        # 2. GERAÇÃO SINGLE
        target_width = int(ih * rw / rh)
        target_height = ih
        if target_width > iw:
            target_width = iw
            target_height = int(iw * rh / rw)

        x_offset = int((final_center_x * iw) - (target_width / 2))
        x_offset = max(0, min(x_offset, iw - target_width))
        y_offset = int((ih - target_height) / 2)

        filter_v = f"crop={target_width}:{target_height}:{x_offset}:{y_offset},setsar=1,setdar={rw}/{rh}"
        if burn_subtitles and srt_path and os.path.exists(srt_path):
            filter_v = _append_subtitle_filter(filter_v, srt_path)

        filter_v += f",scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(ih,iw),min(1080,ih),-2)'"

        cmd = ["ffmpeg", "-i", video_path, "-vf", filter_v, "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-c:a", "copy", "-y", output_path]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_path

    finally:
        if os.path.exists(temp_frames_dir):
            shutil.rmtree(temp_frames_dir)

def _extract_frames_ffmpeg_v7(video_path: str, output_dir: str):
    # Extração de 2 FPS (Garante precisão sem matar o processador)
    cmd = ["ffmpeg", "-i", video_path, "-vf", "fps=2", os.path.join(output_dir, "frame_%04d.jpg"), "-y"]
    subprocess.run(cmd, capture_output=True, check=True)

def _analyze_frames_v7(frames_dir: str) -> List[Dict[str, Any]]:
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
    log = []
    
    for f in frame_files:
        img_path = os.path.join(frames_dir, f)
        frame = cv2.imread(img_path)
        if frame is None: continue
        
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(img_rgb)
        
        candidates = []
        if results.multi_face_landmarks:
            for landmarks in results.multi_face_landmarks:
                x_coords = [lm.x for lm in landmarks.landmark]
                y_coords = [lm.y for lm in landmarks.landmark]
                xmin, xmax = min(x_coords), max(x_coords)
                ymin, ymax = min(y_coords), max(y_coords)
                
                cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
                area = (xmax - xmin) * (ymax - ymin)
                
                # QUANTUM FILTER 1: Blacklist da Mesa (Bonecos)
                # Se estiver muito embaixo (cy > 0.58) rastejando o centro -> Corta fora.
                if cy > 0.58: continue
                
                # QUANTUM FILTER 2: Blacklist de Estáticos Centrais
                # Bonecos de podcast costumam ficar no centro-baixo. 
                # Humanos costumam ocupar as laterais ou centro-alto.
                if 0.4 < cx < 0.6 and cy > 0.5: continue 
                
                # Lips Tracking (Sensibilidade Extrema: 0.006)
                lip_y = [landmarks.landmark[i].y for i in LIP_INDEXES]
                lip_dist = max(lip_y) - min(lip_y)
                is_speaking = lip_dist > 0.007
                
                # Score: Confiança Labial + Posição Realeza (0.32)
                pos_bonus = 1.0 - abs(cy - 0.32)
                score = (100.0 if is_speaking else 0.0) + (pos_bonus * 20.0) + (area * 10.0)
                
                candidates.append({"x": cx, "score": score, "speaking": is_speaking})
        
        if candidates:
            best = max(candidates, key=lambda x: x["score"])
            log.append({
                "center_x": best["x"], 
                "speaking": best["speaking"],
                "all_xs": sorted([c["x"] for c in candidates]),
                "count": len(candidates)
            })
            
    return log

def _get_split_targets_v7(log: List[Dict[str, Any]]) -> List[float]:
    left, right = [], []
    for d in log:
        xs = d.get("all_xs", [])
        if len(xs) >= 2:
            left.append(xs[0])
            right.append(xs[-1])
        elif len(xs) == 1:
            # Se so tem 1, distribui pra onde ele esta pra manter o split estável
            if xs[0] < 0.45: left.append(xs[0])
            elif xs[0] > 0.55: right.append(xs[0])
            
    if not left: left = [0.25]
    if not right: right = [0.75]
    return [float(np.median(left)), float(np.median(right))]

def _execute_stacked_crop_v7(video_path: str, output_path: str, targets: List[float], iw: int, ih: int, format: str, burn_subtitles: bool, srt_path: Optional[str]) -> str:
    # Resolve 1 locutor sendo cortado: Alarga a janela de busca no Stacked
    t1_x, t2_x = int(targets[0] * iw), int(targets[1] * iw)
    win_h = ih // 2
    win_w = int(win_h * 9 / 8) # Janela confortável para um humano sentado
    
    off1_x = max(0, min(t1_x - (win_w // 2), iw - win_w))
    off2_x = max(0, min(t2_x - (win_w // 2), iw - win_w))
    
    filter_complex = (
        f"[0:v]crop={win_w}:{win_h}:{off1_x}:0[top];"
        f"[0:v]crop={win_w}:{win_h}:{off2_x}:0[bottom];"
        f"[top][bottom]vstack=inputs=2,setsar=1,setdar=9/16[v]"
    )
    
    final_v_label = "[v]"
    if burn_subtitles and srt_path and os.path.exists(srt_path):
        clean_sub = srt_path.replace("\\", "/").replace(":", "\\:")
        filter_complex += f";{final_v_label}subtitles='{clean_sub}':force_style='FontSize=12'{final_v_label}"
        
    cmd = ["ffmpeg", "-i", video_path, "-filter_complex", filter_complex, "-map", f"{final_v_label}", "-map", "0:a", "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-c:a", "copy", "-y", output_path]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path

def _append_subtitle_filter(video_filter: str, srt_path: str) -> str:
    style = "Fontname=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=50"
    clean_sub = srt_path.replace("\\", "/").replace(":", "\\:")
    video_filter += f",subtitles='{clean_sub}':force_style='{style}'"
    return video_filter

def _get_video_dims(video_path: str) -> tuple[int, int]:
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w, h = map(int, result.stdout.strip().split('x'))
        return w, h
    except: return 1920, 1080
