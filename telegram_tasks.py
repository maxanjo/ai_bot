from myapp import celery
from multiprocessing import Process


def run_bot_script(api_key, token):
    import telegram_script
    telegram_script.run_bot(api_key, token)

@celery.task()
def run_bot(api_key, token):
    # Create a new process for the bot script
    bot_process = Process(target=run_bot_script, args=(api_key, token))
    bot_pid = bot_process.pid  # Access PID before starting
    # Detach the process from the main process
    bot_process.daemon = True
    bot_process.start()