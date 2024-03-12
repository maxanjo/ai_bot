from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError
import requests
import database_utils from functions
import os
from requests.exceptions import RequestException
import logging
import signal
import time
import argparse

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
    logger = setup_logger('telegram_bot/logs',token)
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

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run a Telegram bot.')
    parser.add_argument('--api-key', help='The Telegram Bot API key.', required=True)
    parser.add_argument('--token', help='The token for the bot.', required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    run_bot(args.api_key, args.token)