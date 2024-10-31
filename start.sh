#!/bin/sh
/usr/local/bin/cloud_sql_proxy -instances=$DB_CONNECTION_NAME=tcp:5432 &
python scrape_and_insert.py --port=${PORT:-8080}
