FROM python:3.13.3

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y ffmpeg && \
    apt-get clean
RUN pip install discord shazamio \
    aiosqlite jishaku "pillow<11.2" bs4 \
    playwright requests "emoji<2.12" \
    pilmoji
RUN playwright install-deps && playwright install

COPY . .

CMD ["python3","bot.py"]