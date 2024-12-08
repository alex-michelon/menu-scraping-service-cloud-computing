import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, request, jsonify
import sqlalchemy
import logging

logging.basicConfig(level=logging.INFO)

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
    try:
        meal_time = request.json.get("meal_time")
        if not meal_time:
            logging.error("meal_time parameter is missing")
            return jsonify({"error": "meal_time is required"}), 400

        url = f"https://liondine.com/{meal_time}"
        logging.info(f"Fetching data from URL: {url}")
        soup = scrape_website(url)
        food_dict = get_food_dict(soup)
        logging.info(f"Fetched food data: {food_dict}")

        with db.connect() as connection:
            for dh, foods in food_dict.items():
                for food in foods:
                    logging.info(f"Inserting data: date={datetime.now().date()}, meal_time={meal_time}, food_item={food},dining_hall={dh}")
                    insert_sql = """
                        INSERT INTO daily_meals (date, meal_time, food_item, dining_hall)
                        VALUES (:date, :meal_time, :food_item)
                    """
                    connection.execute(
                        sqlalchemy.text(insert_sql),
                        {
                            "date": datetime.now().date(),
                            "meal_time": meal_time,
                            "food_item": food.replace("'", "''"),
                            "dining_hall": dh
                        }
                    )
            logging.info("Data insertion completed successfully.")
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"status": "data inserted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
