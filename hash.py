import hashlib

def short_hash(valor: str, length: int = 6) -> str:
    return hashlib.md5(valor.encode()).hexdigest()[:length]
