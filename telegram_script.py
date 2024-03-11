from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError
import requests
import os
from requests.exceptions import RequestException
import logging
import signal
import time

def setup_logger(token):
    # Create the logs directory if it doesn't exist
    log_dir = 'telegram_logs'
    os.makedirs(log_dir, exist_ok=True)

    # Create a log file for the specific token
    log_file = os.path.join(log_dir, f'{token}.log')

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

def start(update, context):
    """Sends a message when the command /start is issued."""
    update.message.reply_text('Hi! Send me something.')

def handle_message(update, context):
    """Handles user messages by sending them to your API and replying with the API's response."""
    user_message = update.message.text
    # Placeholder for API call
    # Example: response_from_api = requests.post('YOUR_API_ENDPOINT', json={'message': user_message}).json()
    update.message.reply_text('hi')

def run_bot(apiKey, token):
    logger = setup_logger(token)
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

if __name__ == '__main__':
    apiKey = '7033603371:AAHd2VujKY8q3IyezStP5X43wBAh9Dfd5qI'  # Replace with your actual apiKey
    run_bot(apiKey, 'token')