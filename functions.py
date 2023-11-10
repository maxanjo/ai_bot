from database_utils import get_project
import os
import re
import sys
import requests
from llama_index.callbacks import CallbackManager, LlamaDebugHandler, CBEventType
from llama_index.llms import OpenAI
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    load_index_from_storage,
    ListIndex,
    StorageContext,
    Prompt,
    ServiceContext
)
from llama_index.logger import LlamaLogger

import openai
import shutil
from dotenv import load_dotenv
load_dotenv()
import mysql.connector
from mysql.connector import Error

storage = 'projects/'
laravel_route_url = f"{os.environ['LARAVEL_API']}/api/update-status-endpoint"

def send_error_payload(task_id, message):
    headers = {
        "Content-Type": "application/json",
    }
    payload_error = {
        "task_id": task_id,
        "status": "FAILED",
        "message": message
    }
    try:
        response = requests.post(laravel_route_url, json=payload_error, headers=headers)
        response.raise_for_status()
        raise Exception(message)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred in send_error_payload function: {e}")
    except Exception as e:
        # Handle your custom exception here
        print(f"Handled Error: {e}")

#Set index with custom folder
def process_set_vector_index(token, task_id):
    project = get_project(token)
    storageProject = f'{storage}{project["id"]}/custom'
    openai.api_key = project['open_ai_api_key']
    llama_logger = LlamaLogger()
    service_context = ServiceContext.from_defaults(llama_logger=llama_logger)

    data_file = os.path.join(storageProject, 'data')
    if os.path.exists(data_file):
        try:
            shutil.rmtree(data_file)
        except OSError as e:
            return send_error_payload(task_id, f"Error removing file: {e}")

    try:
        documents = SimpleDirectoryReader(storageProject).load_data()
    except Exception as e:
        return send_error_payload(task_id, f"Error loading documents: {e}")
    try:
        if project['response_mode'] != 'tree_summarize':
            index = VectorStoreIndex.from_documents(documents, service_context=service_context)
            index.set_index_id("vector_index")
        else:
            index = ListIndex.from_documents(documents)
            index.set_index_id("list_index")
        
        # save index to disk
        index.storage_context.persist(os.path.join(storageProject, 'data'))
        headers = {
            "Content-Type": "application/json",
        }
        # Notify Laravel of success
        payload = {
            "task_id": task_id,
            "status": "COMPLETED",
            "message": "Index has been created"
        }
        response = requests.post(laravel_route_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

    except Exception as e: 
        return handle_openai_exception(task_id, e)

# Define a custom function to handle OpenAI exceptions
def handle_openai_exception(task_id, e):
    if isinstance(e.__cause__, openai.error.AuthenticationError):
        message = "Authentication Error: " + str(e.__cause__)
    elif isinstance(e.__cause__, openai.error.APIError):
        message = "OpenAI API returned an API Error: " + str(e.__cause__)
    elif isinstance(e.__cause__, openai.error.APIConnectionError):
        message = "Failed to connect to OpenAI API: " + str(e.__cause__)
    elif isinstance(e.__cause__, openai.error.RateLimitError):
        message = "OpenAI API request exceeded rate limit: " + str(e.__cause__)
    else:
        message = "Unhandled OpenAI Error: " + str(e)

    return send_error_payload(task_id, message)
