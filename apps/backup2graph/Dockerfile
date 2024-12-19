FROM python:3.12-slim
WORKDIR /app
ENV PATH="$PATH:/app"
COPY requirements.txt requirements.txt
RUN apt update && apt install -y python3-dev cmake make gcc g++ libssl-dev && pip3 install -r requirements.txt
COPY app /app
ENTRYPOINT ["python", "backup2graph.py"] 