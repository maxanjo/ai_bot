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
            # join 'projects' and 'ai_settings' tables using the 'project_id' column
            query = "SELECT p.*, a.* FROM projects p LEFT JOIN ai_settings a ON p.id = a.project_id WHERE p.token = %s"
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (token,))
            project = cursor.fetchone()
            return project
    except mysql.connector.Error as error:
        print("Error while retrieving project details: {}".format(error))
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
