import mysql.connector
from mysql.connector import Error
import os
import sys

import requests

def get_telegram_bot(api_key):
    connection = mysql.connector.connect(
        host=os.environ['HOST'],
        user=os.environ['SPRINTHOSTUSER'],
        password=os.environ['PASSWORD'],
        database=os.environ['DATABASE']
    )
    try:
        if connection.is_connected():
            #p.api, p.product_data, p.website, p.id, u.left_tokens, p.description, ai.temperature, ai.model, ai.prompt, ai.response_mode, p.user_id
            query = """
                SELECT 
                    tb.*, p.id
                FROM telegram_bots tb
                LEFT JOIN projects p ON p.id = tb.project_id    
                WHERE tb.api_key = %s
            """
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (api_key))
            project = cursor.fetchone()
            return project
    except mysql.connector.Error as error:
        print("Error while retrieving project details: {}".format(error))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_project(token, session_id = None):
    connection = mysql.connector.connect(
        host=os.environ['HOST'],
        user=os.environ['SPRINTHOSTUSER'],
        password=os.environ['PASSWORD'],
        database=os.environ['DATABASE']
    )
    try:
        if connection.is_connected():
            #p.api, p.product_data, p.website, p.id, u.left_tokens, p.description, ai.temperature, ai.model, ai.prompt, ai.response_mode, p.user_id
            query = """
                SELECT 
                    p.api, p.product_data, p.website, p.id, p.is_indexed, p.is_active,
                    u.left_tokens, p.description, u.subscription_plan,
                    ai.temperature, ai.model, ai.prompt, ai.response_mode, p.user_id,
                    GROUP_CONCAT(DISTINCT s.name SEPARATOR ', ') AS services,
                    c.answer, c.context
                FROM projects p
                LEFT JOIN ai_settings ai ON p.id = ai.project_id
                LEFT JOIN users u ON p.user_id = u.id
                LEFT JOIN subscriptions s ON p.user_id = s.user_id
                LEFT JOIN chats c ON p.id = c.project_id AND c.session_id = %s
                WHERE p.token = %s
                GROUP BY 
                    p.id, p.api, p.product_data, p.website, 
                    u.left_tokens, p.description, u.subscription_plan,
                    ai.temperature, ai.model, ai.prompt, ai.response_mode, p.user_id,
                    c.answer, c.context
            """
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (session_id, token))
            project = cursor.fetchone()
            return project
    except mysql.connector.Error as error:
        print("Error while retrieving project details: {}".format(error))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def setup_logger(log_dir, filename):
    # Create the logs directory if it doesn't exist
    
    os.makedirs(log_dir, exist_ok=True)

    # Create a log file for the specific filename
    log_file = os.path.join(log_dir, f'{filename}.log')

    # Configure logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create a file handler for the log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create a formatter for the log messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    return logger