timeout = 60
workers = 2  # Number of Gunicorn worker processes
bind = 'api-guru.ru:5000'  # IP address and port to bind to

# Specifies the path to the error log file
errorlog = 'error.log'

# Specifies the path to the access log file
accesslog = 'access.log'

# Specifies the log level to capture everything
loglevel = 'debug'