from flask import Blueprint
from flask import Flask, request, jsonify
from database_utils import get_telegram_bot, setup_logger
import subprocess
telegram_routes = Blueprint('telegram_routes', __name__)


@telegram_routes.route("/start-bot", methods=["POST"])
def start_bot():
    api_key = request.json.get('api-key')
    if not api_key:
        return jsonify({'error': 'Missing api_key in request body'}), 400
    try:
        pr_id = get_telegram_bot(api_key)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({'error': f"An unexpected error occurred: {e}"}), 400
    logger = setup_logger('telegram_bot/logs', f'bot_log_{pr_id}')

    try:
        subprocess.run(['sudo', 'systemctl', 'start', f'telegram_bot_{pr_id}.service'])
        return jsonify({'result': f'Service started successfully'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error starting service: {e.output}'}), 500

@telegram_routes.route("/stop-bot", methods=["POST"]) 
def stop_bot():
    api_key = request.json.get('api-key')
    if not api_key:
        return jsonify({'error': 'Missing api_key in request body'}), 400
    try:
        pr_id = get_telegram_bot(api_key)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({'error': f"An unexpected error occurred: {e}"}), 400
    logger = setup_logger('telegram_bot/logs', f'bot_log_{pr_id}')

    try:
        subprocess.run(['sudo', 'systemctl', 'stop', f'telegram_bot_{pr_id}.service'])
        return jsonify({'result': f'Service  stopped successfully'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error stopping service : {e.output}'}), 500

@telegram_routes.route("/service-status", methods=["POST"])
def service_status():
    api_key = request.json.get('api-key')
    if not api_key:
        return jsonify({'error': 'Missing api_key in request body'}), 400
    try:
        pr_id = get_telegram_bot(api_key)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({'error': f"An unexpected error occurred: {e}"}), 400
    logger = setup_logger('telegram_bot/logs', f'bot_log_{pr_id}')

    try:
        result = subprocess.run(['sudo', 'systemctl', 'status', f'telegram_bot_{pr_id}.service'], capture_output=True, text=True)
        return jsonify({'status': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error getting status for service : {e.output}'}), 500



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