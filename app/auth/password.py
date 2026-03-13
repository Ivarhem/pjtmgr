"""비밀번호 해싱 및 검증 (Python 표준 라이브러리 전용, 외부 의존성 없음).

해시 형식: pbkdf2:{algo}:{iterations}:{salt_hex}:{key_hex}
"""
import hashlib
import hmac
import os
import binascii

_ITERATIONS = 260_000
_ALGO = "sha256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(_ALGO, password.encode(), salt, _ITERATIONS)
    return f"pbkdf2:{_ALGO}:{_ITERATIONS}:{binascii.hexlify(salt).decode()}:{binascii.hexlify(key).decode()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, algo, iters, salt_hex, key_hex = hashed.split(":")
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(key_hex)
        candidate = hashlib.pbkdf2_hmac(algo, password.encode(), salt, int(iters))
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False
