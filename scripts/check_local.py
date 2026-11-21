"""Checks that this machine can run the Decision Register with no admin rights.

Each check is independent, so one failure does not hide the others.
It writes only to a temporary folder and removes its test key afterwards.
"""

import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

KEYRING_SERVICE = "decision-register-check"
KEYRING_USER = "test-key"


def check_python() -> str:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is needed")
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def check_encrypted_database(folder: Path) -> str:
    from sqlcipher3 import dbapi2 as sqlcipher

    path = folder / "register.db"
    key = os.urandom(32).hex()

    db = sqlcipher.connect(str(path))
    db.execute(f"PRAGMA key = \"x'{key}'\"")
    db.execute("CREATE TABLE record (id TEXT PRIMARY KEY, title TEXT)")
    db.execute("INSERT INTO record VALUES ('DEC-1', 'A secret title')")
    db.commit()
    version = db.execute("PRAGMA cipher_version").fetchone()[0]
    db.close()

    raw = path.read_bytes()
    if raw.startswith(b"SQLite format 3") or b"A secret title" in raw:
        raise RuntimeError("the database file is not encrypted")

    db = sqlcipher.connect(str(path))
    db.execute(f"PRAGMA key = \"x'{key}'\"")
    title = db.execute("SELECT title FROM record WHERE id = 'DEC-1'").fetchone()[0]
    db.close()
    if title != "A secret title":
        raise RuntimeError("could not read the data back with the right key")

    print("      (SQLCipher may print 'hmac check failed' next. That is the wrong key being refused.)")
    wrong = sqlcipher.connect(str(path))
    wrong.execute(f"PRAGMA key = \"x'{os.urandom(32).hex()}'\"")
    try:
        wrong.execute("SELECT count(*) FROM record").fetchone()
    except sqlcipher.DatabaseError:
        return f"SQLCipher {version}: encrypted, readable with the key, refused without it"
    finally:
        wrong.close()
    raise RuntimeError("the database opened with the wrong key")


def check_file_encryption() -> str:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    secret = b"An original file"
    locked = AESGCM(key).encrypt(nonce, secret, None)
    if AESGCM(key).decrypt(nonce, locked, None) != secret:
        raise RuntimeError("could not decrypt with the right key")
    try:
        AESGCM(AESGCM.generate_key(bit_length=256)).decrypt(nonce, locked, None)
    except InvalidTag:
        return "AES-256-GCM: files can be locked and unlocked"
    raise RuntimeError("the file decrypted with the wrong key")


def check_key_store() -> str:
    import keyring

    backend = type(keyring.get_keyring()).__name__
    value = os.urandom(16).hex()
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, value)
    try:
        if keyring.get_password(KEYRING_SERVICE, KEYRING_USER) != value:
            raise RuntimeError(f"the key store ({backend}) did not return the key")
    finally:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    return f"key store works ({backend})"


def check_search_index(folder: Path) -> str:
    import chromadb

    client = chromadb.PersistentClient(path=str(folder / "chroma"))
    collection = client.create_collection("check")
    # The first run downloads ChromaDB's built-in model (about 80 MB).
    collection.add(
        ids=["a", "b", "c"],
        documents=[
            "Staff must change their password every ninety days.",
            "The canteen serves lunch from noon.",
            "All servers are patched on the first Sunday of the month.",
        ],
    )
    found = collection.query(query_texts=["How often are passwords rotated?"], n_results=1)
    if found["ids"][0][0] != "a":
        raise RuntimeError(f"search returned the wrong passage: {found['ids'][0][0]}")
    return f"ChromaDB {chromadb.__version__}: built-in model ran here and search found the right passage"


def main() -> int:
    failed = 0
    # ignore_cleanup_errors: Windows can keep ChromaDB's files open until the program ends.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        checks = [
            ("Python", check_python),
            ("Encrypted database", lambda: check_encrypted_database(folder)),
            ("File encryption", check_file_encryption),
            ("Key store", check_key_store),
            ("Search index", lambda: check_search_index(folder)),
        ]
        for name, check in checks:
            try:
                print(f"PASS  {name}: {check()}")
            except Exception as error:  # report every failure, whatever its kind
                failed += 1
                print(f"FAIL  {name}: {type(error).__name__}: {error}")
                print("      " + traceback.format_exc().strip().splitlines()[-2].strip())
    print()
    print("All checks passed." if not failed else f"{failed} check(s) failed. Copy this output back.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
