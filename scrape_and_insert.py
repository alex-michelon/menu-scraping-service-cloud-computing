import os
import requests
from bs4 import BeautifulSoup
import pg8000
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

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
    url = f"https://liondine.com/{meal_time}"
    soup = scrape_website(url)
    food_dict = get_food_dict(soup)

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_connection_name = os.getenv("DB_CONNECTION_NAME")

    connection = pg8000.connect(user=db_user, password=db_password, database=db_name, unix_sock=f'/cloudsql/{db_connection_name}')
    cursor = connection.cursor()

    for category, foods in food_dict.items():
        for food in foods:
            insert_sql = f"""
            INSERT INTO daily_meals (date, meal_time, food_item)
            VALUES ('{datetime.now().date()}', '{meal_time}', '{food.replace("'", "''")}')
            """
            cursor.execute(insert_sql)
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"status": "data inserted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
