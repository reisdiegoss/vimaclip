# =============================================
# VimaClip - Motor de Vídeo
# Serviço de Smart Director Ultra (v21.1 - PURGE BONECO EDITION)
# =============================================
# Foco: Meio Termo + Extermínio Total do Boneco
# Arquitetura: Ultra-Vitality Filter + Dynamic Harmony + Zero-Boneco Deadzone
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

# Inicializa o Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True, 
    max_num_faces=5,
    min_detection_confidence=0.35, 
    min_tracking_confidence=0.5
)

# Constantes de Enquadramento
ASPECT_RATIOS = {
    "vertical": {"width_ratio": 9, "height_ratio": 16},
    "horizontal": {"width_ratio": 16, "height_ratio": 9},
    "square": {"width_ratio": 1, "height_ratio": 1},
}

# Índices para variância labial
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
    Motor Smart Director v21.1 PURGE BONECO:
    - Ultra-Vitality Filter: Threshold labial em 0.0042 (bloqueio total de estáticos).
    - Zero-Boneco Deadzone: Exclusão cirúrgica do centro (onde o boneco mora).
    - Harmonic Balance: Equilíbrio ponderado 65% Host para o "Meio Termo".
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
        # 1. Extração Auditagem Visual
        logger.info(f"[SMART-DIRECTOR v21.1] Executando Purge do Boneco: {base_name}")
        _extract_frames_ffmpeg_v21(video_path, temp_frames_dir)

        # 2. Detecção e Extermínio de Estáticos
        tracking_data = _analyze_purge_v21(temp_frames_dir)
        
        if not tracking_data:
            logger.warning("[SMART-DIRECTOR] Escuridão Total. Alpha 0.35.")
            final_center_x = 0.35
            has_split_tension = False
        else:
            all_centers = [d["center_x"] for d in tracking_data]
            final_center_x = float(np.median(all_centers))
            
            has_split_tension = any(d["has_conflict"] for d in tracking_data)
            multi_presence = sum(1 for d in tracking_data if d["face_count"] >= 2) / len(tracking_data)

            if layout == "auto" and format in ["vertical", "square"] and (has_split_tension or multi_presence > 0.05):
                logger.info("[SMART-DIRECTOR] Ativando SPLIT PURGE (Dual Human Only).")
                targets = _get_split_targets_v21(tracking_data)
                return _execute_stacked_crop_v21(video_path, output_path, targets, iw, ih, burn_subtitles, srt_path)

        # 4. Enquadramento Single ALPHA (O Meio Termo)
        target_width = int(ih * rw / rh)
        target_height = ih
        if target_width > iw:
            target_width = iw
            target_height = int(iw * rh / rw)

        # CÁLCULO DE CROP COM PADDING MILIMÉTRICO
        x_offset = int((final_center_x * iw) - (target_width / 2))
        
        # O MEIO TERMO: Compensação visual para o Host
        if final_center_x > 0.50:
            # Puxamos 15% para a esquerda se o Convidado estiver dominando
            x_offset -= int(0.15 * iw)
        elif final_center_x < 0.38:
            # Se for Host sozinho, damos respiro de 10%
            x_offset -= int(0.10 * iw)

        x_offset = max(0, min(x_offset, iw - target_width))
        y_offset = int((ih - target_height) / 2)

        filter_v = f"crop={target_width}:{target_height}:{x_offset}:{y_offset},setsar=1,setdar={rw}/{rh}"
        if burn_subtitles and srt_path and os.path.exists(srt_path):
            filter_v = _append_subtitle_filter(filter_v, srt_path)

        filter_v += f",scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(ih,iw),min(1080,ih),-2)'"

        logger.info(f"[FFMPEG-PURGE] Success: x={x_offset}, center={final_center_x:.4f}")
        cmd = ["ffmpeg", "-i", video_path, "-vf", filter_v, "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-c:a", "copy", "-y", output_path]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_path

    finally:
        if os.path.exists(temp_frames_dir):
            shutil.rmtree(temp_frames_dir)

def _extract_frames_ffmpeg_v21(video_path: str, output_dir: str):
    cmd = ["ffmpeg", "-i", video_path, "-vf", "fps=3", os.path.join(output_dir, "frame_%04d.jpg"), "-y"]
    subprocess.run(cmd, capture_output=True, check=True)

def _analyze_purge_v21(frames_dir: str) -> List[Dict[str, Any]]:
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
    tracking_log = []
    
    for f in frame_files:
        img_path = os.path.join(frames_dir, f)
        frame = cv2.imread(img_path)
        if frame is None: continue
        
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(img_rgb)
        
        real_humans = []
        if results.multi_face_landmarks:
            for landmarks in results.multi_face_landmarks:
                x_coords = [lm.x for lm in landmarks.landmark]
                y_coords = [lm.y for lm in landmarks.landmark]
                xmin, xmax = min(x_coords), max(x_coords)
                ymin, ymax = min(y_coords), max(y_coords)
                cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
                
                # ZONA ANTI-BONECO (Exclusão Cirúrgica do Eixo Z)
                # 1. Filtro de Mesa
                if cy > 0.60: continue 
                # 2. Filtro de Centro Geométrico (Morte ao Boneco Estático)
                if 0.45 < cx < 0.55 and cy > 0.40: continue 
                
                # 3. ULTRA VITALITY (Threshold 0.0042)
                lip_pts = [landmarks.landmark[i].y for i in LIP_INDEXES]
                v_dist = max(lip_pts) - min(lip_pts)
                
                if v_dist > 0.0042: # Só humanos reais se mexendo tanto
                    real_humans.append(cx)
        
        if real_humans:
            left_wing = [x for x in real_humans if x < 0.45]
            right_wing = [x for x in real_humans if x > 0.55]
            
            # Cálculo Ponderado (Meio Termo)
            if left_wing and right_wing:
                h_x, g_x = float(np.median(left_wing)), float(np.median(right_wing))
                center = (h_x * 0.70) + (g_x * 0.30) # Prioridade máxima ao Host
            else:
                center = float(np.median(real_humans))
            
            tracking_log.append({
                "center_x": center,
                "has_conflict": len(left_wing) > 0 and len(right_wing) > 0,
                "face_count": len(real_humans)
            })
            
    return tracking_log

def _get_split_targets_v21(log: List[Dict[str, Any]]) -> List[float]:
    l_c = [d["center_x"] for d in log if d["center_x"] < 0.45]
    r_c = [d["center_x"] for d in log if d["center_x"] > 0.55]
    return [float(np.median(l_c)) if l_c else 0.30, float(np.median(r_c)) if r_c else 0.70]

def _execute_stacked_crop_v21(video_path: str, output_path: str, targets: List[float], iw: int, ih: int, burn_subtitles: bool, srt_path: Optional[str]) -> str:
    win_h = ih // 2
    win_w = int(win_h * 9 / 4.5) 
    
    off1_x = int((targets[0] * iw) - (win_w / 2))
    if targets[0] < 0.38: off1_x -= int(0.12 * iw)
    off1_x = max(0, min(off1_x, iw - win_w))
    
    off2_x = int((targets[1] * iw) - (win_w / 2))
    if targets[1] > 0.62: off2_x += int(0.12 * iw)
    off2_x = max(0, min(off2_x, iw - win_w))
    
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
    subprocess.run(cmd, capture_output=True, check=True)
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
