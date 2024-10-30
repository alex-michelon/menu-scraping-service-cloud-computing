FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y gcc wget \
    && wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /cloud_sql_proxy \
    && chmod +x /cloud_sql_proxy \
    && pip install -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["/bin/sh", "-c", "/cloud_sql_proxy -dir=/cloudsql -instances=$DB_CONNECTION_NAME & python scrape_and_insert.py --port=$PORT"]
