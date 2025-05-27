from cryptography.fernet import Fernet
import os

class AuthService:
    def __init__(self):
        self.key = os.getenv('secret_key')

    def validate_password(self, password: str) -> dict[str, bool | str]:
        if len(password) < 8:
            return {"is_valid": False, "error_message": "Password must be at least 8 characters long"}
        if not any(c.isupper() for c in password):
            return {"is_valid": False, "error_message": "Password must contain at least one uppercase letter"}
        if not any(c.islower() for c in password):
            return {"is_valid": False, "error_message": "Password must contain at least one lowercase letter"}
        if not any(c.isdigit() for c in password):
            return {"is_valid": False, "error_message": "Password must contain at least one number"}
        return {"is_valid": True, "error_message": "Password is valid"}

    def encrypt_sensitive_data(self, data: str) -> bytes:
        key = os.getenv('secret_key')
        if not key:
            raise ValueError("Secret key is not set")
        f = Fernet(key)
        return f.encrypt(data.encode())

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        key = os.getenv('secret_key')
        if not key:
            raise ValueError("Secret key is not set")
        f = Fernet(key)
        return f.decrypt(encrypted_data).decode()