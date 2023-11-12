import mysql.connector
from mysql.connector import Error
import os
import sys

def get_project(token):
    connection = mysql.connector.connect(
        host=os.environ['HOST'],
        user=os.environ['SPRINTHOSTUSER'],
        password=os.environ['PASSWORD'],
        database=os.environ['DATABASE']
    )
    try:
        if connection.is_connected():
            # join 'projects', 'ai_settings', and 'users' tables using the 'project_id' and 'user_id' columns
            query = """
                SELECT p.*, a.*, u.*
                FROM projects p
                LEFT JOIN ai_settings a ON p.id = a.project_id
                LEFT JOIN users u ON p.user_id = u.id
                WHERE p.token = %s
            """
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (token,))
            project = cursor.fetchone()
            return project
    except mysql.connector.Error as error:
        print("Error while retrieving project details: {}".format(error))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

