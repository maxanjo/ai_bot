from flask import Flask, request, jsonify
from llama_index.logger import LlamaLogger
from database_utils import get_project
from llama_index.callbacks import CallbackManager, LlamaDebugHandler, CBEventType, TokenCountingHandler
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
import json
from llama_index.memory import ChatMemoryBuffer
import time
import hashlib
import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG)

import os
env = os.environ.get('ENVIRONMENT', 'development')
# Check if not production
if env != 'production':
  logging.basicConfig(filename='app.log', level=logging.DEBUG)
  
import sys
from flask_cors import CORS
from flask_cors import cross_origin
from requests.exceptions import HTTPError
import requests
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
import openai
import shutil
from celery import Celery
from unidecode import unidecode
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend='redis://localhost:6379/0',
        broker='redis://localhost:6379/0'
    )

    return celery

celery = make_celery(app)


gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

app.debug = True  # Enable debug mode
CORS(app)
# Get the environment variable for the host

host=os.environ['HOST'],
user=os.environ['SPRINTHOSTUSER'],
password=os.environ['PASSWORD'],
database=os.environ['DATABASE']
storage='projects/'
CORS(app, origins=['https://chatty.guru'])

app.logger.debug("Flask app started")

@app.route("/project/<token>", methods=["GET"])
def projectInfo(token):
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    try:
        if connection.is_connected():
            # join 'projects' and 'ai_settings' tables using the 'project_id' column
            query = "SELECT p.*, a.* FROM projects p LEFT JOIN ai_settings a ON p.id = a.project_id WHERE p.token = %s"
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, (token,))
            project = cursor.fetchone()
            if project:
                return jsonify(project)  # Convert project dictionary to JSON response
            else:
                return jsonify({"message": "Project not found"}), 404  # Return a JSON response for not found
    except mysql.connector.Error as error:
        print("Error while retrieving project details: {}".format(error))
        return jsonify({"message": "Error while retrieving project details"}), 500  # Return a JSON response for server error
    finally:
        if (connection.is_connected()):
            cursor.close()


@app.route("/", methods=["GET"])
def sayHello():
    return 'hello привет', 200
@app.route("/files/<token>", methods=["GET"])
def list_files(token):
    project = get_project(token)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    project_id = project['project_id']
    project_folder = f'{storage}{project_id}'
    files = []
    # Check if the project folder exists
    if os.path.exists(project_folder):
        files = os.listdir(project_folder)

    return jsonify({"files": files, 'id': project_id}), 200

@app.route("/remove/<token>/<filename>", methods=["DELETE"])
def remove_file(token, filename):
    project = get_project(token)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    project_id = project['project_id']
    project_folder = f'{storage}{project_id}'

    # Check if the project folder exists
    if not os.path.exists(project_folder):
        return jsonify({"error": "Project folder not found"}), 404

    file_path = os.path.join(project_folder, filename)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        # Remove the file
        os.remove(file_path)
        return jsonify({"response": "File removed successfully"}), 200
    except OSError as e:
        return jsonify({"error": f"Error removing file: {e}"}), 500

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'rtf', 'txt', 'csv', 'html'}

def is_related_to_products(text):
    user_message = (
        "You are AI assistant for a online shop. You should determine if a client is asking information about a product in our store. " 
        "It can be a question about price, availability in stock, product characteristic, comparing 2 products. In this case you should contruct query parameters based on a client question. Construct them for every mentioned product. "
        "Add sort_price parameter if required ."
        "For example product_name=item_name&color=green&size=44&sort_price=desc|asc. "
        "List of available query parameters: product_name, color, size, weight, material, price, sort_price "
        "Use only these query parameters for consructing. "
        "Write your asnwer as array of json objects. [{url_params: <url_here>, is_related: 'yes', question_type: 'comparing products' | 'product characteristic' }] "
        "If the question is not related to products of the store, then your answer would be [{is_related: 'no'}] "
        "Be strict. Dont write anything else. Your answer will be used for a next query. "
        ""
        f"Client question: {text}"
        "Your answer:"
    )
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=payload)

    
    if response.status_code == 200:
        api_response = response.json()

        if "choices" in api_response and api_response["choices"]:
            choice = api_response["choices"][0]
            
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                try:
                    # Parse the JSON content
                    data = json.loads(content)
                    app.logger.info(data)
                    # Iterate through the data array
                    for item in data:
                        if isinstance(item, str):
                            # Convert the string to a dictionary
                            item = json.loads(item)
                        url_params = item.get("url_params")
                        is_related = item.get("is_related")
                        app.logger.info(url_params)
                        if is_related == "yes" and url_params:
                            from urllib.parse import parse_qs, urlencode
                            param_dict = parse_qs(url_params) 
                            encoded_dict = urlencode(param_dict, doseq=True) 
                            # Make API calls to each URL
                            old_http_proxy = os.environ.get('HTTP_PROXY')  
                            old_https_proxy = os.environ.get('HTTPS_PROXY')

                            # Disable proxy env vars
                            os.environ['HTTP_PROXY'] = ''
                            os.environ['HTTPS_PROXY'] = ''

                            response = requests.get(f'http://wordpress/wp-json/chatty/v1/posts?{encoded_dict}', proxies=None)

                            # Restore old proxy settings
                            os.environ['HTTP_PROXY'] = old_http_proxy
                            os.environ['HTTPS_PROXY'] = old_https_proxy
                            if response.status_code == 200:
                                api_data = response.text
                                app.logger.info(f'api data ' + api_data)
                                return api_data

                            else:
                                return ''
                
                except json.JSONDecodeError as e:
                    return ''

        return ''
    else:
        return ''

    # Handle error, unexpected response, or missing "is_related" key
    return False

def allowed_file(filename):
    # Check if the file has an extension and if the extension is in the allowed set
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/store/<token>", methods=["POST"])
def store_documents(token):
    project = get_project(token)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    project_id = project['project_id']
    # Check if the project folder exists, if not, create it
    project_folder = f'{storage}{project_id}'
    if not os.path.exists(project_folder):
        os.makedirs(project_folder)

    # Check if files were uploaded
    if 'files[]' not in request.files:
        return jsonify({"error": "No files were uploaded"}), 400

    files = request.files.getlist('files[]')

    if not files:
        return jsonify({"error": "No files were uploaded"}), 400

    saved_files = []
    for file in files:
        if file:
            if not allowed_file(file.filename):
                return jsonify({"error": f"Invalid file type. Allowed types: pdf, doc, docx, rtf, txt, csv."}), 400
            
            original_filename = transliterate_and_secure_filename(file.filename)
            
            if '.' not in original_filename: # Check if there is an extension in the filename
                return jsonify({"error": f"Invalid file name. The file must have an extension."}), 400
            
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            
            # Create a unique filename using random_string_part or timestamp
            unique_string = hashlib.sha256((str(time.time()) + original_filename).encode()).hexdigest()[:10]
            filename = f"{unique_string}_{original_filename}"
            file.save(os.path.join(project_folder, filename))
            saved_files.append({'name': filename, 'pr_id': project_id})

    return jsonify({"response": "Files uploaded successfully", "files": saved_files}), 200

@app.route("/exists/<id>/<filename>")
def check_file_existence(id, filename):
    storage_folder = f"projects/{id}"
    file_path = os.path.join(storage_folder, filename)

    if os.path.exists(file_path):
        return jsonify({"exists": True}), 200
    else:
        return jsonify({"exists": False}), 404

@app.route("/index/<token>", methods=["GET"])
def setIndex(token):
    from tasks import set_vector_index_task
    task = set_vector_index_task.apply_async(args=[token])
    return jsonify({'message': 'Task started', 'task_id': task.id}), 202
   
import tiktoken
@app.route("/projects/<token>/<session_id>", methods=["POST"])
# @cross_origin(origin='http://127.0.0.1:8000')
def get_project_details(token, session_id):
    query_text = request.json.get("text", None)
    product_response = is_related_to_products(query_text)
  
    project = get_project(token)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    allowed_website = project.get('website')
    openai.api_key = os.environ['OPENAI_API_KEY']
    storageProject = f'{storage}{project["project_id"]}/data'
    allowed_website = project.get('website')  # replace 'website' with the actual key used in your project data
    laravel_api_referer = os.environ.get('LARAVEL_API')

    # Check if the request comes from an allowed website or the specified Laravel API Referer
    if 'Referer' not in request.headers or (
        allowed_website not in request.headers['Referer'] and
        laravel_api_referer not in request.headers['Referer']
    ):
        return jsonify({'error': 'Access restricted'}), 403

    left_tokens = project.get('left_tokens', 0)
    memory = ChatMemoryBuffer.from_defaults(token_limit=1500)
    # Check if there are enough tokens
    if left_tokens < 10000:
        return jsonify({'error': 'Not enough tokens'}), 403  # You can use 403 or another appropriate HTTP status code
    # convert description from bytes to string

    token_counter = TokenCountingHandler(
        tokenizer=tiktoken.encoding_for_model("gpt-3.5-turbo").encode
    )
    if project['description']:
        project['description'] = project['description'].decode()
    
        # rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir=storageProject)

    temperature = float(project['temperature'])
    llm = OpenAI(model=project['model'], temperature=temperature)
    llama_debug = LlamaDebugHandler(print_trace_on_end=True)
    callback_manager = CallbackManager([llama_debug, token_counter])
    service_context = ServiceContext.from_defaults(callback_manager=callback_manager, llm=llm)
    prompt = project['prompt'] + '. \n Information about product ' + product_response

    # load index
    try:
        if(project['response_mode'] != 'tree_summarize'):
            index = load_index_from_storage(storage_context, index_id="vector_index")
        else:
            index = load_index_from_storage(storage_context, index_id="list_index")
        
        # ... Your other code ...
    except Exception as e:
        app.logger.error("An error occurred:", exc_info=True)  # Log the full exception traceback
    if(project['response_mode'] != 'tree_summarize'):
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=prompt,
            service_context=service_context, response_mode=project['response_mode']
        )
    else:
        query_engine = index.as_query_engine(service_context=service_context, response_mode=project['response_mode'])  
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    try:
        response = chat_engine.chat(query_text)
    except Exception as e:
        app.logger.error("An error occurred:", exc_info=True)
        if isinstance(e.__cause__, openai.error.AuthenticationError):
            return jsonify({'error_message': "Authentication Error: " + str(e.__cause__)}), 500
        if isinstance(e.__cause__, openai.error.APIError):
            return jsonify({'error_message': "OpenAI API returned an API Error: " + str(e.__cause__)}), 500
        if isinstance(e.__cause__, openai.error.APIConnectionError ):
            return jsonify({'error_message': "Failed to connect to OpenAI API: " + str(e.__cause__)}), 500
        if isinstance(e.__cause__, openai.error.RateLimitError ):
            return jsonify({'error_message': "OpenAI API request exceeded rate limit: " + str(e.__cause__)}), 500
        else:
            return jsonify({'error_message': str(e)}), 500
    event_pairs = llama_debug.get_llm_inputs_outputs()
    logs = event_pairs[0][0]
    content = logs.payload
    result = {'result': response.response, 'logs': str(event_pairs)}
    llama_debug.flush_event_logs()
    from tasks import send_chat_request
    send_chat_request.apply_async(args=[project['user_id'], project['id'], session_id, token_counter.total_llm_token_count,f"Client: {query_text},\nAi response: {response.response}"])
    
        
    return jsonify(result), 200


def transliterate_and_secure_filename(filename):

    # Separate name and extension
    if '.' in filename:
        name, ext = filename.rsplit('.', 1)
    else:
        return secure_filename(filename)
    
    # Transliterate non-ASCII characters and secure the filename
    transliterated_name = unidecode(name)
    secured_filename = secure_filename(f"{transliterated_name}.{ext}")
    
    return secured_filename
    
if __name__ == '__main__':
    app.run()

