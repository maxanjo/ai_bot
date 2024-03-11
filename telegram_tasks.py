from telegram_script import setup_logger, run_bot_script
from multiprocessing import Process

def start_bot(api_key, token):
    logger = setup_logger(token)
    logger.info(f"Initilizing process")

    # Create a new process for the bot script
    bot_process = Process(target=run_bot_script, args=(api_key, token))

    # Access PID before starting
    # Detach the process from the main process
    bot_process.daemon = True
    bot_process.start()
    bot_pid = bot_process.pid

    logger.info(f"Created bot process with PID {bot_pid}")
    logger.info("Bot process started")

    terminate_running_processes(token)