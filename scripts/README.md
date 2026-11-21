# Local check

Proves that a machine can run the Decision Register with no admin rights and no Docker.
It tests the encrypted database, file encryption, the key store and ChromaDB with its built-in model.

It writes only to a temporary folder. The first run downloads ChromaDB's model (about 80 MB).

## Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r scripts\requirements-check.txt
.venv\Scripts\python scripts\check_local.py
```

## macOS and Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements-check.txt
.venv/bin/python scripts/check_local.py
```

Every line starts with `PASS` or `FAIL`. If anything fails, copy the whole output.
