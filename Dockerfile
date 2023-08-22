# Using on x86_64 or amd64
#FROM python:3.11-slim

# Using on arm64v8
FROM arm64v8/python:3.11.3-slim

WORKDIR /app

COPY . .

RUN chmod ugo+x start.sh && \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install -r requirements.txt

EXPOSE 80

CMD ["./start.sh"]