from functions import process_set_vector_index
from telegram_tasks import run_bot
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
    'Authorization': f'Bearer {os.environ.get("FLASK_API_TOKEN")}'
}

def run_bot_script(api_key, token):
    import telegram_script
    telegram_script.run_bot(api_key, token)

@celery.task()
def create_bot_task(api_key, token):
    from telegram_script import setup_logger
    from multiprocessing import Process
    try:
        logger = setup_logger(token)
        logger.info(f"Initilizing process")
        # Create a new process for the bot script
        bot_process = Process(target=run_bot_script, args=(api_key, token))
        

        # Access PID before starting
        # Detach the process from the main process
        bot_process.daemon = True
        bot_process.start()
        bot_pid = bot_process.pid
        logger.info(f"Created bot process with PID {bot_pid}")
        logger.info("Bot process started")
        terminate_running_processes(token)  
    except Exception as e:
        logger.error(f"An error occurred while running the bot: {e}")

running_processes = []
def terminate_running_processes(token):
    from telegram_script import setup_logger
    logger = setup_logger(token)
    for process in running_processes:
        try:
            logger.info(f"Bot process {process.pid}")
            process.terminate()
            logger.info(f"Terminated process with PID {process.pid}")
        except ProcessLookupError:
            # Process might have already terminated
            pass

    # Clear the list of running processes
    running_processes.clear()

@celery.task()
def send_chat_request(user_id, project_id, session, total_tokens, answer, context, playground):
    chatData = {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session,
        "total_tokens": total_tokens,
        "answer": answer,
        "playground": playground,
        "context": context
    }

    try:
        # Make API calls to each URL
        old_http_proxy = os.environ.get('HTTP_PROXY')  
        old_https_proxy = os.environ.get('HTTPS_PROXY')

        # Disable proxy env vars
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''

        response = requests.post(
            f'{os.environ.get("LARAVEL_API")}/api/chat/update',
            json=chatData,
            headers=headers  # Include the headers in the request
        )
         # Restore old proxy settings
        os.environ['HTTP_PROXY'] = old_http_proxy
        os.environ['HTTPS_PROXY'] = old_https_proxy
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")

@celery.task()
def sendEmbeddingRequest(user_id, total_tokens, project_id):
    chatData = {
        "user_id": user_id,
        "total_tokens": total_tokens,
        "project_id": project_id
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