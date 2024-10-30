import os
import pg8000
from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["POST"])
def create_table():
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_connection_name = os.getenv("DB_CONNECTION_NAME")

    connection = pg8000.connect(user=db_user, password=db_password, database=db_name, unix_sock=f'/cloudsql/{db_connection_name}')
    cursor = connection.cursor()

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS daily_meals (
        date DATE,
        meal_time VARCHAR(10),
        food_item VARCHAR(255)
    );
    """
    cursor.execute(create_table_sql)
    connection.commit()
    cursor.close()
    connection.close()
    return "Table created successfully", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
