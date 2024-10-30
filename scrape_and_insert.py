import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, request, jsonify
import sqlalchemy

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
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.content, 'html.parser')

def get_food_dict(soup):
    food_dict = {}
    h3_tags = soup.find_all('h3')
    for h3 in h3_tags:
        food_names = []
        for nxt in h3.findAllNext():
            if nxt.name == 'h3':
                break
            if nxt.name == 'div' and 'food-name' in nxt.get('class', []):
                food_names.append(nxt.text.strip())
        if food_names:
            food_dict[h3.text.strip()] = food_names
    return food_dict

@app.route("/", methods=["POST"])
def scrape_and_insert():
    meal_time = request.json.get("meal_time")
    if not meal_time:
        return jsonify({"error": "meal_time is required"}), 400

    url = f"https://liondine.com/{meal_time}"
    try:
        soup = scrape_website(url)
        food_dict = get_food_dict(soup)
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch meal data: {e}"}), 500

    try:
        with db.connect() as connection:
            for category, foods in food_dict.items():
                for food in foods:
                    insert_sql = """
                    INSERT INTO daily_meals (date, meal_time, food_item)
                    VALUES (:date, :meal_time, :food_item)
                    """
                    connection.execute(
                        sqlalchemy.text(insert_sql),
                        {"date": datetime.now().date(), "meal_time": meal_time, "food_item": food}
                    )
    except Exception as e:
