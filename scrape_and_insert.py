import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, request, jsonify, g
import sqlalchemy
import logging
import uuid
from google.cloud.logging import Client as LoggingClient

logging_client = LoggingClient()
logging_client.setup_logging()

app = Flask(__name__)

def init_db_connection():
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_connection_name = os.getenv("DB_CONNECTION_NAME")
    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_password,
            database=db_name,
            query={"unix_sock": f"/cloudsql/{db_connection_name}/.s.PGSQL.5432"},
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

db = init_db_connection()

def scrape_website(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.content, 'html.parser')

def get_food_dict(soup):
    food_dict = {}
    h3_tags = soup.find_all('h3')
    for h3 in h3_tags:
        lines = {"":[]}
        food_names = []
        line_type = ""
        for nxt in h3.findAllNext():
            if nxt.name == 'h3':
                break
            if nxt.name == 'div' and 'food-type' in nxt.get('class', []):
                line_type = nxt.text.strip()
                lines[line_type] = []
            elif nxt.name == 'div' and 'food-name' in nxt.get('class', []):
                lines[line_type].append(nxt.text.strip())
        if not len(lines[""]):
            del lines[""]
        if any(values for values in lines.values() if values):
            food_dict[h3.text.strip()] = lines
    return food_dict

@app.before_request
def start_timer():
    g.start_time = datetime.utcnow()
    g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    g.trace_id = trace_header.split("/")[0] if trace_header else None

@app.after_request
def log_request(response):
    duration = (datetime.utcnow() - g.start_time).total_seconds()
    log_message = f"Request: {request.method} {request.url} | Status: {response.status_code} | Duration: {duration:.3f}s | CorrelationID: {g.correlation_id} | TraceID: {g.trace_id}"
    logging.info(log_message)
    response.headers["X-Correlation-ID"] = g.correlation_id
    return response

def log_with_trace_and_correlation(message, level=logging.INFO):
    trace_message = f"{message} | CorrelationID: {g.correlation_id} | TraceID: {g.trace_id}" if g.trace_id else message
    logging.log(level, trace_message)

@app.route("/", methods=["POST"])
def scrape_and_insert():
    try:
        meal_time = request.json.get("meal_time")
        if not meal_time:
            log_with_trace_and_correlation("meal_time parameter is missing", logging.ERROR)
            return jsonify({"error": "meal_time is required"}), 400

        url = f"https://liondine.com/{meal_time}"
        log_with_trace_and_correlation(f"Fetching data from URL: {url}")
        soup = scrape_website(url)
        food_dict = get_food_dict(soup)
        log_with_trace_and_correlation(f"Fetched food data: {food_dict}")

        with db.connect() as connection:
            for dh, lines in food_dict.items():
                for line, foods in lines.items():
         
