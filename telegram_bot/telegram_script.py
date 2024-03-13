from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError
import requests
from database_utils import get_telegram_bot, setup_logger
import os
from requests.exceptions import RequestException
import logging
import signal
import time
import argparse

mainLogger = setup_logger('telegram_bot/logs',f'logs')


def start(update, context):
    """Sends a message when the command /start is issued."""
    update.message.reply_text('Hi! Send me something.')

def handle_message(update, context):
    """Handles user messages by sending them to your API and replying with the API's response."""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    token = context.bot_data['token'] # Replace with your actual API token

    api_url = f"{os.environ.get('DOMAIN')}/projects/{token}/{chat_id}"

    # Send a request to the API
    response = requests.post(api_url, json={'text': user_message})
    if response.status_code == 200:
        api_response = response.json()
        mainLogger.info(api_response)
        mainLogger.info(api_response['result'])

        # Handle the API response
        update.message.reply_text(api_response['result'])
    else:
        mainLogger.info(api_response['An error occurred while processing your request.'])
        update.message.reply_text('An error occurred while processing your request.')
    # Placeholder for API call
    # Example: response_from_api = requests.post('YOUR_API_ENDPOINT', json={'message': user_message}).json()
    update.message.reply_text(response.result)

def run_bot(apiKey):
    try:
        project_details = get_telegram_bot(api_key)
    except Exception as e:
        mainLogger.info(f"Failed to get project and run_bot script for {apiKey}")
        return

    project_id = project_details['project_id']
    bot_status = project_details['status']
    token = project_details['token']
    logger = setup_logger('telegram_bot/logs',f'project_{project_id}')
    if bot_status == 0:
        logger.info(f"Bot status is disabled. The bot has not started")
        return

    logger.info("Bot has started")
    """Runs the bot in an infinite loop with error handling."""
    def handle_sigterm(sig, frame):
        logger.info("Termination signal received. Stopping bot...")
        updater.stop()
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    try:
        updater = Updater(apiKey, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        context = dp.bot.context
        context.bot_data['token'] = token
        updater.start_polling()
        updater.idle()
    except RequestException as e:
        logger.error(f"Network error occurred: {e}")
        from time import sleep
        max_retries = 5
        retry_interval = 5  # seconds
        for attempt in range(max_retries):
            try:
                # Your network request here
                break  # If successful, exit the loop
            except RequestException as e:
                logger.error(f"Network error occurred: {e}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    sleep(retry_interval)
                else:
                    logger.error("Max retries reached. Exiting.")
                    # Handle max retries reached (e.g., raise the exception or exit)
                    break
    except TelegramError as e:
        logger.error(f"Telegram API error: {e}")
        # Handle Telegram-specific errors (e.g., rate limits)
    except OSError as e:
        logger.error(f"Process-related error: {e}")
        # Potentially critical error. Decide on action: retry, log, or exit.
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        # General catch-all for unexpected errors
    finally:
        # Clean-up actions, if any
        logger.info("Bot shutdown process completed.")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run a Telegram bot.')
    parser.add_argument('--api-key', help='The Telegram Bot API key.', required=True)
    parser.add_argument('--token', help='The token for the bot.', required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    run_bot(args.api_key, args.token)