from database_utils import get_project
import os
import re
import sys
import requests
from llama_index.callbacks import CallbackManager, LlamaDebugHandler,TokenCountingHandler, CBEventType
from llama_index.llms import OpenAI, MockLLM
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    load_index_from_storage,
    ListIndex,
    StorageContext,
    set_global_service_context,
    Prompt,
    MockEmbedding,
    ServiceContext
)
import tiktoken
from myapp import celery
from celery.exceptions import SoftTimeLimitExceeded
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
        'Origin': 'https://api-guru.ru',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.environ.get("FLASK_API_TOKEN")}'
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


@celery.task(bind=True, soft_time_limit=600, hard_time_limit=650)
#Set index with custom folder
def process_set_vector_index(self, token, task_id):
    try:
        token_counter = TokenCountingHandler(
            tokenizer=tiktoken.encoding_for_model("gpt-3.5-turbo").encode
        )

        callback_manager = CallbackManager([token_counter])
        llm = MockLLM(max_tokens=256)
        embed_model = MockEmbedding(embed_dim=1536)
    
        project = get_project(token)
        if(project['left_tokens'] < 10000):
            send_error_payload(task_id, "Недостаточно токенов")
            return
        storageProject = f'{storage}{project["id"]}'
        folder_size = calculate_folder_size(storageProject)
        if(not project['services'] and folder_size > 2):
            send_error_payload(task_id, "Files must be less than 2 MB. But a subscription plan to increase limits")
            return
        if(folder_size > 50):
            send_error_payload(task_id, "Files must be less than 50 mb")
            return
        openai.api_key = os.environ['OPENAI_API_KEY']
        llama_logger = LlamaLogger()
        set_global_service_context(
            service_context = ServiceContext.from_defaults(llama_logger=llama_logger, llm=llm, embed_model=embed_model, callback_manager=callback_manager)
        )
        data_file = os.path.join(storageProject, 'data')
        if os.path.exists(data_file):
            try:
                shutil.rmtree(data_file)
            except OSError as e:
                print(e)
                return send_error_payload(task_id, f"Error removing file: {e}")

        try:
            documents = SimpleDirectoryReader(storageProject).load_data()
        except Exception as e:
            print(e)
            return send_error_payload(task_id, f"Error loading documents: {e}")
        try:
            if project['response_mode'] != 'tree_summarize':
                index = VectorStoreIndex.from_documents(documents)
                index.set_index_id("vector_index")
            else:
                index = ListIndex.from_documents(documents)
                index.set_index_id("list_index")
            
            # save index to disk
            index.storage_context.persist(os.path.join(storageProject, 'data'))
            spent_tokens = token_counter.total_embedding_token_count / 10
            from tasks import sendEmbeddingRequest
            sendEmbeddingRequest.apply_async(args=[project['user_id'], spent_tokens, project["id"]])
    
            # reset counts
            token_counter.reset_counts()

            headers = {
                "Content-Type": "application/json",
                'Authorization': f'Bearer {os.environ.get("FLASK_API_TOKEN")}'
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
    
    except SoftTimeLimitExceeded:
        send_error_payload(task_id, "Task took too long and was interrupted")
        raise SoftTimeLimitExceeded("Task took too long and was interrupted.")

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

def calculate_folder_size(folder_path):
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)

    # Convert bytes to megabytes
    total_size_mb = total_size / (1024 * 1024)

    return total_size_mb