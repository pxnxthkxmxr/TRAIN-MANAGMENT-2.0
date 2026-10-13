
import hashlib
import os
import re
from database import execute_query, fetch_one


def hash_password(password: str, salt: str = None) -> tuple:
    """Hash a password using PBKDF2-HMAC-SHA256 with salt."""
    if not salt:
        salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(stored_hash: str, stored_salt: str, provided_password: str) -> bool:
    """Verify if provided password matches the stored hash."""
    calc_hash, _ = hash_password(provided_password, stored_salt)
    return calc_hash == stored_hash


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate 10-digit phone number."""
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 10


def register_user(username: str, password: str, full_name: str, email: str, phone: str, role: str = 'passenger') -> tuple:
    """
    Register a new user in the system.
    Returns (success: bool, message: str, user_id: int or None).
    """
    username = username.strip().lower()
    full_name = full_name.strip()
    email = email.strip().lower()
    phone = phone.strip()

    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters long.", None

    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    if not full_name:
        return False, "Full name cannot be empty.", None

    if not validate_email(email):
        return False, "Invalid email address format.", None

    if not validate_phone(phone):
        return False, "Phone number must be a valid 10-digit number.", None

    if role not in ('admin', 'staff', 'passenger'):
        return False, f"Invalid role: '{role}'. Must be admin, staff, or passenger.", None

    # Check if username or email already exists
    existing_user = fetch_one("SELECT id FROM users WHERE username = ?", (username,))
    if existing_user:
        return False, f"Username '{username}' is already taken.", None

    existing_email = fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing_email:
        return False, f"Email '{email}' is already registered.", None

    pwd_hash, salt = hash_password(password)

    try:
        user_id = execute_query(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, phone, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, pwd_hash, salt, full_name, email, phone, role)
        )
        return True, "Registration successful!", user_id
    except Exception as e:
        return False, f"Failed to register user: {str(e)}", None


def login_user(username: str, password: str) -> tuple:
    """
    Authenticate a user by username and password.
    Returns (success: bool, message: str, user_dict: dict or None).
    """
    username = username.strip().lower()
    user = fetch_one("SELECT * FROM users WHERE username = ?", (username,))

    if not user:
        return False, "Invalid username or password.", None

    if not verify_password(user['password_hash'], user['salt'], password):
        return False, "Invalid username or password.", None

    # Strip sensitive security data before returning
    user_data = {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'email': user['email'],
        'phone': user['phone'],
        'role': user['role'],
        'created_at': user['created_at']
    }
    return True, f"Welcome back, {user['full_name']}!", user_data


def get_user_by_id(user_id: int) -> dict:
    """Get sanitized user dictionary by ID."""
    user = fetch_one("SELECT id, username, full_name, email, phone, role, created_at FROM users WHERE id = ?", (user_id,))
    return user


def change_password(user_id: int, old_password: str, new_password: str) -> tuple:
    """Change a user's password."""
    user = fetch_one("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
    if not user:
        return False, "User not found."

    if not verify_password(user['password_hash'], user['salt'], old_password):
        return False, "Current password is incorrect."

    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    pwd_hash, salt = hash_password(new_password)
    execute_query(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (pwd_hash, salt, user_id)
    )
    return True, "Password changed successfully."
