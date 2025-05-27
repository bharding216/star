#!/usr/bin/env python3
import sys
import os
import subprocess
from dotenv import load_dotenv, dotenv_values

# Client config for startup
CLIENTS = {
    'star': {
        'env_file': '.env.star',
        'client_name': 'star',
        'description': 'Star application',
        'port': 2000
    },
    'se_legacy': {
        'env_file': '.env.se_legacy', 
        'client_name': 'se_legacy',
        'description': 'SE Legacy application',
        'port': 2001
    }
}

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <client_name>")
        print("Available clients:")
        for name, config in CLIENTS.items():
            print(f"  {name}: {config['description']}")
        sys.exit(1)
    
    client_key = sys.argv[1]
    
    if client_key not in CLIENTS:
        print(f"Unknown client: {client_key}")
        print(f"Available: {', '.join(CLIENTS.keys())}")
        sys.exit(1)
    
    client_config = CLIENTS[client_key]
    
    # Set environment variables
    env_vars = dotenv_values(client_config['env_file'])
    for key, value in env_vars.items():
        if value is not None:
            os.environ[key] = value
    os.environ['PORT'] = str(client_config['port'])
    
    print(f"Starting {client_config['description']}...")
    print(f"Client: {client_config['client_name']}")
    print(f"Port: {client_config['port']}")
    print(f"Running at http://localhost:{client_config['port']}")
    
    try:
        # Run the Flask app
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)

if __name__ == '__main__':
    main()