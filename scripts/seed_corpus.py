import json
import sys
from pathlib import Path

import httpx

API_URL = "http://localhost:8000/api/v1/ingest"
SEED_FILE = Path(__file__).parent / "seed_docs.json"


def main():
    docs = json.loads(SEED_FILE.read_text())
    print(f"Ingesting {len(docs)} docs ...")

    for doc in docs:
        resp = httpx.post(API_URL, json=doc, timeout=30.0)
        if resp.status_code != 200:
            print(f"    FAILED [{doc['source']}]: {resp.status_code} {resp.test}")
            sys.exit(1)
        result = resp.json()
        print(f"    OK [{doc['source']}]: {result}")

    print("Done.")


if __name__ == "__main__":
    main()