from myapp import celery
from multiprocessing import Process
from telegram_script import setup_logger

def run_bot_script(api_key, token):
    import telegram_script
    telegram_script.run_bot(api_key, token)

@celery.task()
def run_bot(api_key, token):
    try:
        logger.info(f"Initilizing process")
        # Create a new process for the bot script
        bot_process = Process(target=run_bot_script, args=(api_key, token))
        bot_pid = bot_process.pid
        logger = setup_logger(token)
        logger.info(f"Created bot process with PID {bot_pid}")

        # Access PID before starting
        # Detach the process from the main process
        bot_process.daemon = True
        # bot_process.start()
        logger.info("Bot process started")

    except Exception as e:
        logger.error(f"An error occurred while running the bot: {e}")