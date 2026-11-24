FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config curl \
        libavformat-dev libavcodec-dev libavutil-dev libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY . .
RUN pip install --no-cache-dir --no-build-isolation -e .

EXPOSE 8000
# Analyze the sample clip (downloaded if missing), then serve the viewer.
CMD ["sh", "-c", "[ -f data/sample.mp4 ] || ./scripts/fetch_sample.sh; python -m vsg.pipeline data/sample.mp4 --out output --stride 3 && python -m vsg.server --out output --host 0.0.0.0 --port 8000"]
