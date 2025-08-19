import logging
from flask import current_app, session
from dotenv import load_dotenv
from pathlib import Path
import pymysql
import pymysql.cursors
import os
import json
from datetime import datetime

# Load .env from repository root if present
load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def get_db_connection(schema: str | None = None):
    """Return a PyMySQL connection using a DictCursor.

    If `schema` is provided, it will be used as the database name; otherwise
    the `MYSQL_DATABASE` env var is used.
    """
    try:
        host = os.getenv('MYSQL_HOST', 'localhost')
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = schema or os.getenv('MYSQL_DATABASE', '')
        port = int(os.getenv('MYSQL_PORT', '3306'))

        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database or None,
            port=port,
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4',
            autocommit=False,
        )
        return conn
    except Exception as err:
        try:
            current_app.logger.error(f"Erreur de connexion DB: {err}")
        except Exception:
            # current_app may not be available in some script contexts
            logging.error(f"Erreur de connexion DB: {err}")
        raise

