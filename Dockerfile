FROM python:3.9-slim

WORKDIR /app

COPY cloud_sql_proxy /usr/local/bin/cloud_sql_proxy
RUN chmod +x /usr/local/bin/cloud_sql_proxy

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV PORT=8080

CMD ["/start.sh"]
