from flask import session
from typing import Any, Optional
from enum import Enum, auto

class SessionKeys(Enum):
    """Enum containing all session key constants."""
    USER_TYPE = 'user_type'
    USER_ID = 'user_id'
    AUTH_TOKEN = 'auth_token'
    LAST_ACTIVITY = 'last_activity'
    THEME = 'theme'
    LANGUAGE = 'language'

class SessionManager:
    """A utility class to manage Flask session variables."""
    
    @staticmethod
    def set(key: SessionKeys, value: Any) -> None:
        """Set a session variable.
        
        Args:
            key (SessionKeys): The session key enum
            value (Any): The value to store
        """
        session[key.value] = value
    
    @staticmethod
    def get(key: SessionKeys, default: Any = None) -> Any:
        """Get a session variable.
        
        Args:
            key (SessionKeys): The session key enum
            default (Any, optional): Default value if key doesn't exist. Defaults to None.
            
        Returns:
            Any: The session value or default if not found
        """
        return session.get(key.value, default)
    
    @staticmethod
    def delete(key: SessionKeys) -> None:
        """Delete a session variable.
        
        Args:
            key (SessionKeys): The session key enum to delete
        """
        session.pop(key.value, None)
    
    @staticmethod
    def clear() -> None:
        """Clear all session variables."""
        session.clear()
    
    @staticmethod
    def has(key: SessionKeys) -> bool:
        """Check if a session variable exists.
        
        Args:
            key (SessionKeys): The session key enum to check
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        return key.value in session
    
    @staticmethod
    def get_user_type() -> Optional[str]:
        """Get the current user type from session.
        
        Returns:
            Optional[str]: The user type or None if not set
        """
        return session.get(SessionKeys.USER_TYPE.value)
    
    @staticmethod
    def set_user_type(user_type: str) -> None:
        """Set the user type in session.
        
        Args:
            user_type (str): The user type to store
        """
        session[SessionKeys.USER_TYPE.value] = user_type
