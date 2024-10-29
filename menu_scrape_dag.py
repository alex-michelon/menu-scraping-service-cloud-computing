from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.cloud_sql import CloudSQLExecuteQueryOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

PROJECT_ID = "cumulonimbus-439521"
INSTANCE_NAME = os.getenv("DB_INSTANCE_CONNECTION_NAME", "cumulonimbus-439521:us-central1:cumulonimbus-cloud-sql")
DATABASE_NAME = os.getenv("DB_NAME", "cumulonimbus")

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

def generate_insert_statements(meal_time, **context):
    url = f"https://liondine.com/{meal_time}"
    soup = scrape_website(url)
    sql_statements = []
    if soup:
        food_dict = get_food_dict(soup)
        for category, foods in food_dict.items():
            for food in foods:
                insert_sql = f"""
                INSERT INTO daily_meals (date, meal_time, food_item)
                VALUES ('{datetime.now().date()}', '{meal_time}', '{food.replace("'", "''")}')
                """
                sql_statements.append(insert_sql)
    return sql_statements

with DAG(
    'daily_meal_scrape',
    default_args=default_args,
    description='Scrape and store daily meal data',
    schedule_interval='@daily',
    start_date=days_ago(1),
    catchup=False,
) as dag:

    create_table_task = CloudSQLExecuteQueryOperator(
        task_id='create_food_table',
        sql="""
        CREATE TABLE IF NOT EXISTS daily_meals (
            date DATE,
            meal_time VARCHAR(10),
            food_item VARCHAR(255)
        );
        """,
        instance=INSTANCE_NAME,
        database=DATABASE_NAME,
        project_id=PROJECT_ID,
        gcp_conn_id='google_cloud_default',
    )

    meal_times = ['breakfast', 'lunch', 'dinner', 'latenight']
    for time in meal_times:
        scrape_and_insert_task = PythonOperator(
            task_id=f'scrape_and_generate_inserts_{time}',
            python_callable=generate_insert_statements,
            op_kwargs={'meal_time': time},
            provide_context=True
        )

        insert_data_task = CloudSQLExecuteQueryOperator(
            task_id=f'insert_food_data_{time}',
            sql="{{ task_instance.xcom_pull(task_ids='scrape_and_generate_inserts_" + time + "') }}",
            instance=INSTANCE_NAME,
            database=DATABASE_NAME,
            project_id=PROJECT_ID,
            gcp_conn_id='google_cloud_default',
        )

        create_table_task >> scrape_and_insert_task >> insert_data_task
