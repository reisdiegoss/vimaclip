# 🎬 VimaClip - Motor de Vídeo

Microsserviço Docker para processamento de vídeos curtos. Roda isolado como API local na porta `8000`, consumido pelo Frontend/Backend principal.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────┐
│  FORA DO DOCKER (Sua Máquina)                       │
│  ┌─────────────┐     ┌──────────────────┐           │
│  │  Frontend    │────▶│ Backend Principal│           │
│  │  React.js    │     │  Node.js/Python  │           │
│  └─────────────┘     └───────┬──────────┘           │
│                              │ HTTP                  │
│  ┌───────────────────────────▼──────────────────┐   │
│  │  DOCKER (Motor de Vídeo - porta 8000)         │   │
│  │  ┌──────────┐ ┌──────┐ ┌──────┐ ┌─────────┐ │   │
│  │  │ FastAPI   │ │FFmpeg│ │yt-dlp│ │MediaPipe│ │   │
│  │  └──────────┘ └──────┘ └──────┘ └─────────┘ │   │
│  └──────────────────────┬───────────────────────┘   │
│                         │ HTTPS                      │
│  ┌──────────────────────▼───────────────────────┐   │
│  │  NUVEM (IA de Áudio)                          │   │
│  │  API Groq (Whisper) ou Deepgram               │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 🚀 Como Rodar

### Pré-requisitos

- Docker Desktop instalado e rodando
- Porta 8000 livre

### Passo a Passo

```powershell
# 1. Entre na pasta do motor de vídeo
cd video-engine

# 2. Copie o arquivo de variáveis de ambiente
copy .env.example .env

# 3. (Opcional) Edite o .env com suas chaves de API
notepad .env

# 4. Suba o container (primeira vez demora uns 5 min por causa das dependências)
docker-compose up --build

# 5. Acesse a documentação Swagger
# Abra no navegador: http://localhost:8000/docs
```

### Comandos Úteis

```powershell
# Rodar em background
docker-compose up -d

# Ver logs em tempo real
docker-compose logs -f

# Parar o container
docker-compose down

# Rebuild depois de mudar código
docker-compose up --build
```

## 📡 Endpoints da API

### `GET /` — Health Check

Verifica se o motor está rodando.

**Resposta:**

```json
{
  "status": "online",
  "service": "VimaClip Motor de Vídeo",
  "version": "1.0.0"
}
```

### `POST /api/engine/cut` — Processar Vídeo

Rota principal. Baixa, corta, transcreve e aplica crop.

**Request:**

```json
{
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "vertical",
  "layout": "single",
  "segments": [
    {"start": "00:10", "end": "00:30"}
  ]
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Vídeo processado com sucesso! 1 segmento(s) gerado(s).",
  "original_video": "/app/temp_videos/job_abc123/video.mp4",
  "segments": [
    {
      "segment_index": 0,
      "start": "00:10",
      "end": "00:30",
      "output_path": "/app/temp_videos/job_abc123/video_seg00.mp4",
      "cropped_path": "/app/temp_videos/job_abc123/video_seg00_cropped_vertical.mp4"
    }
  ],
  "transcription": {
    "text": "Olá pessoal...",
    "language": "pt",
    "words": [...]
  },
  "metadata": {
    "job_id": "abc123",
    "title": "Título do vídeo",
    "duration": 180
  }
}
```

### `GET /api/engine/jobs` — Listar Jobs

Lista todos os jobs com arquivos temporários.

### `DELETE /api/engine/cleanup/{job_id}` — Limpar Arquivos

Remove arquivos temporários de um job.

## 📁 Estrutura de Pastas

```
video-engine/
├── Dockerfile              # Imagem Docker (Python + FFmpeg)
├── docker-compose.yml      # Orquestração do container
├── requirements.txt        # Dependências Python
├── .env                    # Variáveis de ambiente (local)
├── .env.example            # Template de variáveis
├── .dockerignore           # Arquivos ignorados pelo Docker
├── README.md               # Este arquivo
├── temp_videos/            # Vídeos temporários (volume Docker)
└── app/
    ├── __init__.py
    ├── main.py              # FastAPI + rotas + pipeline
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py       # Modelos Pydantic (request/response)
    └── services/
        ├── __init__.py
        ├── downloader.py    # Download com yt-dlp
        ├── cutter.py        # Corte com FFmpeg
        ├── transcriber.py   # Transcrição (mock Groq)
        └── cropper.py       # Smart Crop (mock MediaPipe)
```

## ⚙️ Hardware Mínimo

| Componente | Requisito | Usado Para |
|---|---|---|
| CPU | 4+ cores | FFmpeg, MediaPipe |
| RAM | 8GB+ | Processamento de vídeo |
| GPU | Não necessária | Tudo roda na CPU |
| Disco | 10GB+ livres | Vídeos temporários |

> **Otimizado para:** Ryzen 7 2700 (8 cores), 32GB RAM, GTX 970 (não utilizada).
