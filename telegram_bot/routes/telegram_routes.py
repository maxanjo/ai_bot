from flask import Blueprint
from flask import Flask, request, jsonify
import subprocess
telegram_routes = Blueprint('telegram_routes', __name__)

@telegram_routes.route("/start-bot", methods=["POST"])
def start_bot():
    service_name = request.json.get('service_name')
    if not service_name:
        return jsonify({'error': 'Missing service_name in request body'}), 400

    try:
        subprocess.run(['sudo', 'systemctl', 'start', service_name])
        return jsonify({'result': f'Service {service_name} started successfully'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error starting service {service_name}: {e.output}'}), 500

   
def stop_bot():
    service_name = request.json.get('service_name')
    if not service_name:
        return jsonify({'error': 'Missing service_name in request body'}), 400

    try:
        subprocess.run(['sudo', 'systemctl', 'stop', service_name])
        return jsonify({'result': f'Service {service_name} stopped successfully'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error stopping service {service_name}: {e.output}'}), 500

@telegram_routes.route("/service-status", methods=["POST"])
def service_status():
    service_name = request.json.get('service_name')
    if not service_name:
        return jsonify({'error': 'Missing service_name in request body'}), 400

    try:
        result = subprocess.run(['sudo', 'systemctl', 'status', service_name], capture_output=True, text=True)
        return jsonify({'status': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error getting status for service {service_name}: {e.output}'}), 500
