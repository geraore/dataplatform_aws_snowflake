import base64
import datetime
import hashlib

import jwt
from cryptography.hazmat.primitives import serialization


def load_private_key(pem: str, passphrase: str | None):
    pw = passphrase.encode() if passphrase else None
    return serialization.load_pem_private_key(pem.encode(), password=pw)


def public_key_fingerprint(private_key) -> str:
    """SHA-256 fingerprint of the DER-encoded public key (Snowflake JWT format)."""
    der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return "SHA256:" + base64.b64encode(hashlib.sha256(der).digest()).decode()


def make_jwt(account: str, user: str, private_key, fingerprint: str) -> str:
    account = account.upper()
    user = user.upper()
    qualified = f"{account}.{user}"
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    payload = {
        "iss": f"{qualified}.{fingerprint}",
        "sub": qualified,
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")
