import mysql.connector
from mysql.connector import Error
import os
import sys

import requests



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
                    p.api, p.product_data, p.website, p.id, 
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

