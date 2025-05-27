import os
import sys
import traceback
from project import create_app

# Add more detailed logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Required environment variables
    required_env_vars = ['CLIENT_NAME', 'secret_key', 'secret_admin_code']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f'Missing required environment variables: {", ".join(missing_vars)}')
        raise ValueError(f'Missing required environment variables: {", ".join(missing_vars)}')

    client_name = os.getenv('CLIENT_NAME')
    if not client_name:
        logger.error('CLIENT_NAME environment variable is not set')
        raise ValueError('CLIENT_NAME environment variable is not set')

    # Validate client_name
    valid_clients = ['star', 'se_legacy']
    if client_name not in valid_clients:
        logger.error(f'Invalid CLIENT_NAME: {client_name}. Must be one of: {", ".join(valid_clients)}')
        raise ValueError(f'Invalid CLIENT_NAME: {client_name}. Must be one of: {", ".join(valid_clients)}')

    logger.info(f"Creating app for client: {client_name}")
    
    # Check some key environment variables
    postgres_vars = ['postgres_user', 'postgres_password', 'postgres_host', 'postgres_db']
    for var in postgres_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"{var}: {'*' * min(len(value), 8)} (length: {len(value)})")
        else:
            logger.warning(f"{var}: NOT SET")
    
    try:
        app = create_app(client_name)
        logger.info("App created successfully!")
    except Exception as app_error:
        logger.error(f"Error during app creation: {str(app_error)}")
        logger.error(f"App error type: {type(app_error).__name__}")
        logger.error(f"App error traceback: {traceback.format_exc()}")
        raise
    
except Exception as e:
    logger.error(f"Failed to create app: {str(e)}")
    logger.error(f"Exception type: {type(e).__name__}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    # Re-raise the exception so Heroku can see it
    raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '2000'))
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=os.getenv('APP_MODE') == 'DEV',
        ssl_context=None,
        threaded=True
    )