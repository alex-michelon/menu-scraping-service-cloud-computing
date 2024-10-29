from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def create_food_table():
    postgres_hook = PostgresHook(postgres_conn_id="cumulonimbus_menu_items")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS daily_meals (
        date DATE,
        meal_time VARCHAR(10),
        food_item VARCHAR(255)
    );
    """
    postgres_hook.run(create_table_sql)

def scrape_website(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

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

def insert_food_data(meal_time):
    url = f"https://liondine.com/{meal_time}"
    soup = scrape_website(url)
    if soup:
        food_dict = get_food_dict(soup)
        postgres_hook = PostgresHook(postgres_conn_id="my_postgres_conn")
        
        insert_sql = """
        INSERT INTO daily_meals (date, meal_time, food_item)
        VALUES (%s, %s, %s)
        """
        for category, foods in food_dict.items():
            for food in foods:
                postgres_hook.run(insert_sql, parameters=(datetime.now().date(), meal_time, food))

with DAG(
    'daily_meal_scrape',
    default_args=default_args,
    description='Scrape and store daily meal data',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    create_table_task = PythonOperator(
        task_id='create_food_table',
        python_callable=create_food_table
    )

    meal_times = ['breakfast', 'lunch', 'dinner', 'latenight']
    for time in meal_times:
        scrape_and_insert_task = PythonOperator(
            task_id=f'insert_food_data_{time}',
            python_callable=insert_food_data,
            op_kwargs={'meal_time': time}
        )
        
        create_table_task >> scrape_and_insert_task