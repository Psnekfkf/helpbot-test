# Amvera (и большинство PaaS без shell-доступа) не даёт ставить
# системные пакеты (apt-get) во время работы бота — только во время
# СБОРКИ образа. Поэтому ffmpeg (нужен для распознавания голосовых,
# см. services/shazam_service.py) ставим здесь, а не руками в "консоли".
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
