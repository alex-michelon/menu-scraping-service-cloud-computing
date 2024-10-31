FROM python:3.9-slim

WORKDIR /app

COPY cloud_sql_proxy /usr/local/bin/cloud_sql_proxy
RUN chmod +x /usr/local/bin/cloud_sql_proxy

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=8080

CMD ["/bin/sh", "-c", "/usr/local/bin/cloud_sql_proxy -instances=$DB_CONNECTION_NAME=tcp:5432 & python scrape_and_insert.py --port=${PORT}"]
