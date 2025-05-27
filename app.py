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

# Validate client_name
valid_clients = ['star', 'se_legacy']
if client_name not in valid_clients:
    raise ValueError(f'Invalid CLIENT_NAME: {client_name}. Must be one of: {", ".join(valid_clients)}')

print(f"Creating app for client: {client_name}")
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