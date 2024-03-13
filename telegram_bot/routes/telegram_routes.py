from flask import Blueprint
from flask import Flask, request, jsonify
from database_utils import get_telegram_bot, setup_logger
import subprocess
import os

telegram_routes = Blueprint('telegram_routes', __name__)


@telegram_routes.route("/start-bot", methods=["POST"])
def start_bot():
    api_key = request.json.get('api-key')
    if not api_key:
        return jsonify({'error': 'Missing api_key in request body'}), 400
    try:
        project_details = get_telegram_bot(api_key)
        project_id = project_details['project_id']
        create_service(api_key, f'telegram_bot_{project_id}.service')
    except Exception as e:
        return jsonify({'error': e}), 400
    logger = setup_logger('telegram_bot/logs', f'project_{project_id}')

    try:
        subprocess.run(['sudo', 'systemctl', 'start', f'telegram_bot_{project_id}.service'])
        return jsonify({'result': f'Service started successfully'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error starting service: {e.output}'}), 500

@telegram_routes.route("/stop-bot", methods=["POST"]) 
def stop_bot():
    api_key = request.json.get('api-key')
    project_details, service_path, error_response = get_project_details_and_service_path(api_key)

    if error_response:
        return error_response
    logger = setup_logger('telegram_bot/logs', f'project_{project_id}')

    try:
        subprocess.run(['sudo', 'systemctl', 'stop', f'telegram_bot_{project_id}.service'])
        return jsonify({'result': f'Service  stopped successfully'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error stopping service : {e.output}'}), 500

@telegram_routes.route("/remove-bot", methods=["POST"])
def remove_bot():
    api_key = request.json.get('api-key')
    project_details, service_path, error_response = get_project_details_and_service_path(api_key)

    if error_response:
        return error_response
    
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', f'telegram_bot_{project_id}.service'])
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error stopping service : {e.output}'}), 500
    log_file_path = f"telegram_bot/logs/project_{project_id}"
    if os.path.isfile(log_file_path):
        os.remove(log_file_path)
    service_file_path = f"/etc/systemd/system/telegram_bot_{project_id}.service"
    if os.path.isfile(service_file_path):
        os.remove(service_file_path)
    reload_result = subprocess.run(["sudo", "systemctl", "daemon-reload"], capture_output=True, text=True)
    if reload_result.returncode != 0:
        mainLogger.error(f"Could not reload systemd daemon: {reload_result.stderr}")
    return jsonify({"result": "Bot is removed successfully"}), 200

@telegram_routes.route("/service-status", methods=["POST"])
def service_status():
    api_key = request.json.get('api-key')
    project_details, service_path, error_response = get_project_details_and_service_path(api_key)

    if error_response:
        return error_response

    logger = setup_logger('telegram_bot/logs', f'project_{project_id}')

    try:
        result = subprocess.run(['sudo', 'systemctl', 'status', f'telegram_bot_{project_id}.service'], capture_output=True, text=True)
        return jsonify({'status': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error getting status for service : {e.output}'}), 500



@telegram_routes.route("/restart-bot", methods=["POST"])
def restart_bot():
    api_key = request.json.get('api-key')
    project_details, service_path, error_response = get_project_details_and_service_path(api_key)

    if error_response:
        return error_response

    project_id = project_details['project_id']
    logger = setup_logger('telegram_bot/logs', f'project_{project_id}')

    try:
        # Stop the bot
        subprocess.run(['sudo', 'systemctl', 'stop', f'telegram_bot_{project_id}.service'])
        logger.info(f'Service stopped: telegram_bot_{project_id}.service')

        # Restart the bot
        subprocess.run(['sudo', 'systemctl', 'restart', f'telegram_bot_{project_id}.service'])
        logger.info(f'Service restarted: telegram_bot_{project_id}.service')

        return jsonify({'result': f'Service restarted successfully'})

    except subprocess.CalledProcessError as e:
        logger.error(f'Error restarting service: {e.output}')
        return jsonify({'error': f'Error restarting service: {e.output}'}), 500

def create_service(bot_api_key, service_file):
    service_path = f"/etc/systemd/system/{service_file}"
    service_content = f"""[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/root/ai_bot/myenv/bin/python3.11 /root/ai_bot/telegram_bot/telegram_script.py --api-key={bot_api_key}
Restart=always

[Install]
WantedBy=multi-user.target
"""

    try:
        if not os.path.exists(service_path):
            with open(service_path, "w") as f:
                f.write(service_content)
            # Reload systemd daemon
            reload_result = subprocess.run(["sudo", "systemctl", "daemon-reload"], capture_output=True, text=True)
            if reload_result.returncode != 0:
                raise Exception(f"Could not reload systemd daemon: {reload_result.stderr}")

            # Start the service
            start_result = subprocess.run(["sudo", "systemctl", "start", service_file], capture_output=True, text=True)
            if start_result.returncode != 0:
                raise Exception(f"Could not start service {service_file}: {start_result.stderr}")

    except Exception as e:
        raise Exception(f"Error: {e}")

def service_file_exists(service_file):
    service_path = f"/etc/systemd/system/{service_file}"

    if not os.path.isfile(service_path):
        raise FileNotFoundError(f"Service file not found: {service_path}")

    return service_path

def get_project_details_and_service_path(api_key):
    if not api_key:
        return jsonify({'error': 'Missing api_key in request body'}), 400

    try:
        project_details = get_telegram_bot(api_key)
        project_id = project_details['project_id']
        service_path = service_file_exists(f"telegram_bot_{project_id}.service")
        return project_details, service_path, None

    except FileNotFoundError as e:
        return None, None, jsonify({'error': str(e)}), 404

    except Exception as e:
        return None, None, jsonify({'error': f"An unexpected error occurred: {e}"}), 400