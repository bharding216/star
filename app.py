import os
from project import create_app

client_name = os.getenv('CLIENT_NAME')
if client_name is None:
    raise ValueError('CLIENT_NAME is not set')

app = create_app(client_name)

if __name__ == '__main__':
    if 'DYNO' in os.environ:
        # Running on Heroku, use gunicorn
        port = int(os.environ.get('PORT', '5000'))
        app.run(host='0.0.0.0', port=port)
    else:
        # Running locally
        port = int(os.environ.get('PORT', '2000'))
        app.run(host='0.0.0.0', port=port, debug=True)