import hmac
import hashlib

def validate_signature(secret: str, raw_body: bytes, actual: str) -> bool:
    expected = hmac.new(secret.encode(), raw_body, digestmod=hashlib.sha256).hexdigest() #creates an HMAC object using your secret as the key and SHA256 as the hashing algorithm on raw_body
    return hmac.compare_digest(expected, actual.split("sha256=")[-1]) # retrieves the signature from the header and removes the "sha256=" prefix to get the actual signature value, then compares it to the expected signature using a secure comparison method