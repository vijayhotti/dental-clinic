import os
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up logging to file
log_dir = '/tmp'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

file_handler = RotatingFileHandler(os.path.join(log_dir, 'application.log'),
                                 maxBytes=1024 * 1024, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

logger.info('Dental Clinic startup')

try:
    from app import app as application
    logger.info('Application imported successfully')
    # Ensure the instance directory exists with proper permissions
    instance_path = '/var/app/current/instance'
    if not os.path.exists(instance_path):
        os.makedirs(instance_path, mode=0o775)
        logger.info(f'Created instance directory at {instance_path}')
    
    # Initialize the database
    from app import init_db
    init_db()
    logger.info('Database initialized successfully')
except Exception as e:
    logger.error(f'Error initializing application: {str(e)}', exc_info=True)
    raise 