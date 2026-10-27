import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from config import JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET


def hash_password(password):
    salt = os.urandom(16)
    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return "$".join(
        [
            "scrypt",
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(password_hash).decode("ascii"),
        ]
    )


def verify_password(password, stored_password_hash):
    algorithm, encoded_salt, encoded_hash = stored_password_hash.split("$")

    if algorithm != "scrypt":
        return False

    salt = base64.b64decode(encoded_salt)
    expected_hash = base64.b64decode(encoded_hash)
    candidate_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )

    return hmac.compare_digest(candidate_hash, expected_hash)


def create_access_token(user_id, username):
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=JWT_EXPIRATION_HOURS
    )

    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
