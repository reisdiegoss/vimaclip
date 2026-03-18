# =============================================
# VimaClip - Motor de Vídeo
# Dockerfile para o microsserviço de processamento
# =============================================

# Imagem base leve do Python 3.10
FROM python:3.10-slim

# Metadados do container
LABEL maintainer="VimaClip Team"
LABEL description="Motor de vídeo para edição de vídeos curtos"

# Variável de ambiente para evitar que o Python gere arquivos .pyc
# e para forçar o output sem buffer (logs aparecem em tempo real)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# =============================================
# INSTALAÇÃO DO FFMPEG
# O FFmpeg é o coração do processamento de vídeo.
# Sem ele, nada de corte, crop ou conversão funciona.
# =============================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    # libgl1 é necessário para o OpenCV funcionar corretamente
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências primeiro (otimiza cache do Docker)
# Se o requirements.txt não mudar, essa camada é reaproveitada
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação para dentro do container
COPY . .

# Cria a pasta temporária para armazenar vídeos baixados e processados
RUN mkdir -p /app/temp_videos

# Expõe a porta 8000 para acesso externo
EXPOSE 8000

# Comando para iniciar o servidor FastAPI via Uvicorn
# --host 0.0.0.0: aceita conexões de qualquer IP (necessário no Docker)
# --port 8000: porta do servidor
# --reload: reinicia automaticamente quando o código muda (dev mode)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
