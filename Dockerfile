FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
CMD ["cloud_sql_proxy", "-instances=<your-cloud-sql-instance-connection-name>=tcp:5432", "&", "python", "scrape_and_insert.py"]
