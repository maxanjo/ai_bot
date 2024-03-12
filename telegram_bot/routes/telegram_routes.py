from flask import Blueprint
from flask import Flask, request, jsonify
import subprocess
telegram_routes = Blueprint('telegram_routes', __name__)

@telegram_routes.route("/start-bot", methods=["POST"])
def start_bot():
    try:
        subprocess.run(['sudo', 'systemctl', 'start', 'telegram_script.service'])
        return jsonify({'result': 'Service started successfully'}) 
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error starting service: {e.output}'}), 500
   
@telegram_routes.route("/stop-bot", methods=["POST"])
def stop_bot():
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', 'telegram_script.service'])
        return jsonify({'result': 'Service stopped successfully'}) 
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error stopping service: {e.output}'}), 500

@telegram_routes.route('/service-status')
def service_status():
    try:
        result = subprocess.run(['sudo', 'systemctl', 'status', 'your_service_name'], capture_output=True, text=True)
        return jsonify({'status': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error getting service status: {e.output}'}), 500