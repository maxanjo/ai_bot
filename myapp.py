from flask import Flask, request, jsonify
# from llama_index import LLMPredictor, GPTSimpleVectorIndex, PromptHelper, ServiceContext, SimpleDirectoryReader,  QuestionAnswerPrompt
# from langchain.chat_models import ChatOpenAI
# from langchain import OpenAI
from llama_index.logger import LlamaLogger
from llama_index import load_index_from_storage, StorageContext

from llama_index.callbacks import CallbackManager, LlamaDebugHandler, CBEventType
from llama_index.llms import OpenAI
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    load_index_from_storage,
    StorageContext,
    Prompt,
    ServiceContext
)


import os
import sys
from flask_cors import CORS
from flask_cors import cross_origin
from requests.exceptions import HTTPError
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
import openai
import shutil

app = Flask(__name__)
app.debug = True  # Enable debug mode
CORS(app)
# Get the environment variable for the host

my_host = 'chatty.guru'
host = "chatty.guru"
user = "a0130638_darius"
password = "09081993"
database = "a0130638_chatty"
storage = 'projects/'

# my_host = '127.0.0.1:8000'
# host = "localhost"
# user = "root"
# password = ""
# database = "ai"
# storage = 'projects/'

CORS(app, origins=['https://chatty.guru'])

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

# define the function to retrieve project details
def get_project(token):
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
            return project
    except mysql.connector.Error as error:
        print("Error while retrieving project details: {}".format(error))
    finally:
        if (connection.is_connected()):
            cursor.close()

@app.route("/", methods=["GET"])
def sayHello():
    return 'hello привет', 200
@app.route("/files/<project_id>", methods=["GET"])
def list_files(project_id):
    project_folder = f'{storage}{project_id}'
    files = []
    # Check if the project folder exists
    if os.path.exists(project_folder):
        files = os.listdir(project_folder)

    return jsonify({"files": files, 'id': project_id}), 200

@app.route("/remove/<project_id>/<filename>", methods=["DELETE"])
def remove_file(project_id, filename):
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

def allowed_file(filename):
    # Check if the file has an extension and if the extension is in the allowed set
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/store/<id>", methods=["POST"])
def store_documents(id):
    # Check if the project folder exists, if not, create it
    project_folder = f'{storage}{id}'
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
            # Securely generate a filename and save the file to the project folder
            filename = secure_filename(file.filename)
            file.save(os.path.join(project_folder, filename))
            saved_files.append({'name': filename, 'pr_id': id})

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
    referer = request.headers.get('Referer')
    domain = referer.split('/')[2] if referer else None
    # if domain != my_host:
    #     return jsonify({'error_message': f'Forbidden'}), 403
    project = get_project(token)
    storageProject = f'{storage}{project["id"]}'
    os.environ["OPENAI_API_KEY"] = project['open_ai_api_key']
    openai.api_key = os.environ["OPENAI_API_KEY"]
    llama_logger = LlamaLogger()
    service_context = ServiceContext.from_defaults(llama_logger=llama_logger)
    if not os.path.exists(storageProject):
        return 'Folder does not exist', 422
    if len(os.listdir(storageProject)) == 0:
        return 'Folder is empty. Add some files', 422
    else:
        data_file = os.path.join(storageProject, 'data')
        if os.path.exists(data_file):
            try:
                shutil.rmtree(data_file)
            except OSError as e:
                return jsonify({"error": f"Error removing file: {e}"}), 500
        documents = SimpleDirectoryReader(storageProject).load_data()
        try:
            index = VectorStoreIndex.from_documents(documents, service_context=service_context)
            # save index to disk
            index.set_index_id("vector_index")
            index.storage_context.persist(f'{storageProject}/data')
        except Exception as e:
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
        return 'Index has been created', 200
   

@app.route("/projects/<token>", methods=["GET"])
# @cross_origin(origin='http://127.0.0.1:8000')
def get_project_details(token): 
    project = get_project(token)  
    os.environ['OPENAI_API_KEY'] = project['open_ai_api_key']
    openai.api_key = os.environ["OPENAI_API_KEY"]
    storageProject = f'{storage}{project["id"]}/data'
    if not project:
        return jsonify({'error': 'Project not found'}), 404    
    # convert description from bytes to string
    if project['description']:
        project['description'] = project['description'].decode()
    
        # rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir=storageProject)

    temperature = float(project['temperature'])
    llm = OpenAI(model=project['model'], temperature=temperature)
    llama_debug = LlamaDebugHandler(print_trace_on_end=True)
    callback_manager = CallbackManager([llama_debug])
    service_context = ServiceContext.from_defaults(callback_manager=callback_manager, llm=llm)
    query_text = request.args.get("text", None)
    prompt = project['prompt']
    template = (
        prompt
    )
    qa_template = Prompt(template)
    # load index
    index = load_index_from_storage(storage_context, index_id="vector_index")
    if(project['response_mode'] == 'compact'):
        query_engine = index.as_query_engine(text_qa_template=qa_template, service_context=service_context, response_mode='compact')
    else:
        query_engine = index.as_query_engine(service_context=service_context, response_mode=project['response_mode'], similarity_top_k=5)  
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    try:
        response = query_engine.query(query_text)
    except Exception as e:
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
    return jsonify(result), 200







    # if(project['model'] == 'gpt-3.5-turbo'):
    #     llm_predictor = LLMPredictor(llm=ChatOpenAI(temperature=temperature, model_name="gpt-3.5-turbo", max_tokens=project['max_tokens']))
    # else:
    #     llm_predictor = LLMPredictor(llm=OpenAI(temperature=temperature, model_name=project['model'], max_tokens=project['max_tokens']))
    
    # llama_logger = LlamaLogger()
    # # define prompt helper
    # # set maximum input size
    # max_input_size = project['max_input_size']
    # # set number of output tokens
    # num_output = project['num_output']
    # # set maximum chunk overlap
    # max_chunk_overlap = project['max_chunk_overlap']
    # context_window = 4097
    # prompt_helper = PromptHelper(context_window, num_output, max_chunk_overlap)
    # service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper, llama_logger=llama_logger)

    # index = GPTSimpleVectorIndex.load_from_disk(f'{storageProject}/data.json', service_context=service_context)

    # # return project details as JSON
    # query_text = request.args.get("text", None)
    # if query_text is None:
    #   return "No text found, please include a ?text=blah parameter in the URL", 400
    # query_history = request.args.get("history", None)
    # if query_history is None:
    #   return "No history found, please include a ?history parameter in the URL", 400
    # prompt = project['prompt']
    # if query_history != '':
    #     prompt = project['prompt'].replace("{chat_history}", 'History of your conversation: ' + query_history)
    # else:
    #     prompt = project['prompt'].replace("{chat_history}", '')

    # QA_PROMPT_TMPL = (
    #     prompt
    # )
    # QA_PROMPT = QuestionAnswerPrompt(QA_PROMPT_TMPL)

  
    
    # try:
    #     response = index.query(query_text, text_qa_template=QA_PROMPT, response_mode=project['response_mode'])
    #     result = {'result': response, 'logs': llama_logger.get_logs()}  # prints all logs, which basically includes all LLM inputs and responses
    #     llama_logger.reset() 
    # except Exception as e:
    #     if isinstance(e.__cause__, openai.error.AuthenticationError):
    #         return jsonify({'error_message': "Authentication Error: " + str(e.__cause__)}), 500
    #     if isinstance(e.__cause__, openai.error.APIError):
    #         return jsonify({'error_message': "OpenAI API returned an API Error: " + str(e.__cause__)}), 500
    #     if isinstance(e.__cause__, openai.error.APIConnectionError ):
    #         return jsonify({'error_message': "Failed to connect to OpenAI API: " + str(e.__cause__)}), 500
    #     if isinstance(e.__cause__, openai.error.RateLimitError ):
    #         return jsonify({'error_message': "OpenAI API request exceeded rate limit: " + str(e.__cause__)}), 500
    #     else:
    #         return jsonify({'error_message': str(e)}), 500


    # return jsonify(result), 200


if __name__ == '__main__':
    app.run()

