import os
import sys

def generate_sha512_hash(password):
    """Generates a SHA-512 crypt hash compatible with Linux shadow/userconf.txt."""
    try:
        import crypt
        return crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    except ImportError:
        print("[FATAL] The 'crypt' module is required to hash passwords securely on Linux.")
        sys.exit(1)

def write_file(path, content, mode=0o600):
    """Writes a file with strict permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with open(os.open(path, os.O_CREAT | os.O_WRONLY, mode), 'w', encoding='utf-8') as f:
        f.write(content)
