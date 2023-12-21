from functions import process_set_vector_index
from myapp import celery
import os
import requests
#Set index with DATA folder
@celery.task(bind=True)
def set_vector_index_task(self, token):
    return process_set_vector_index(token, self.request.id)

import requests
import os

headers = {
        'Origin': 'https://api-guru.ru',
        'Content-Type': 'application/json',
    }

@celery.task()
def send_chat_request(user_id, project_id, session, total_tokens, answer):
    chatData = {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session,
        "total_tokens": total_tokens,
        "answer": answer
    }

    
    
    try:
        response = requests.post(
            f'{os.environ.get("LARAVEL_API")}/api/chat/update',
            json=chatData,
            headers=headers  # Include the headers in the request
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")

@celery.task()
def sendEmbeddingRequest(user_id, total_tokens):
    chatData = {
        "user_id": user_id,
        "total_tokens": total_tokens
    }
    
    try:
        response = response = requests.post(
            f'{os.environ.get("LARAVEL_API")}/api/chat/embedding',
            json=chatData,
            headers=headers
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")