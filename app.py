import os
from project import create_app

# Required environment variables
required_env_vars = ['CLIENT_NAME', 'secret_key', 'secret_admin_code']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f'Missing required environment variables: {", ".join(missing_vars)}')

client_name = os.getenv('CLIENT_NAME')
if not client_name:
    raise ValueError('CLIENT_NAME environment variable is not set')
app = create_app(client_name)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '2000'))
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=os.getenv('FLASK_ENV') == 'development',
        ssl_context=None,
        threaded=True
    )