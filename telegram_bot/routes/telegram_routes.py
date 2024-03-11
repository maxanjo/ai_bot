from flask import Blueprint
from flask import Flask, request, jsonify

telegram_routes = Blueprint('telegram_routes', __name__)

@telegram_routes.route("/create_bot", methods=["POST"])
def create_bot():
    # Get bot information from request data (assuming POST request)
    data = request.get_json()  # Replace with your preferred method to get data
    api_key = data.get('api_key')
    token = data.get('token')

    if not api_key or not token:
        return jsonify({'error': 'Missing bot name or username'}), 400

    from tasks import create_bot_task
    task = create_bot_task.apply_async(args=[api_key, token])

    return jsonify({'message': 'Telegram bot creation initiated', 'task_id': task.id})
   