from app.utils import validate_signature
import hmac, hashlib

def test_valid_signature():
    secret = "supersecretkey"
    body = b'{"test": "hello"}'
    # compute the expected signature the same way your function does
    expected_signature = "sha256=" + hmac.new(secret.encode(), body, digestmod=hashlib.sha256).hexdigest()
    # then assert validate_signature returns True
    assert validate_signature(secret, body, expected_signature) == True

def test_invalid_signature():
    secret = "supersecretkey"
    body = b'{"test": "hello"}'
    wrong_signature = "sha256=wrongsignature"
    assert validate_signature(secret, body, wrong_signature) == False