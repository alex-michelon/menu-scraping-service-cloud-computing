FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install requests beautifulsoup4 flask pg8000
CMD ["python", "scrape_and_insert.py"]
