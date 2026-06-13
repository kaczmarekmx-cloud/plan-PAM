import requests
import json
import hashlib
import os
import base64
import csv
import io
from datetime import datetime

SHEET_ID = "1YeDuROB0ghVP0vluJi1yWNOogJSwtIsC"
GID = "21253449"
EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&id={SHEET_ID}&gid={GID}"DATA_FILE = "data.json"
HASH_FILE = "data_hash.txt"
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

def fetch_sheet():
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    resp = requests.get(EXPORT_URL, headers=headers, timeout=30, allow_redirects=True)
    print(f"Status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type','')}")
    if resp.status_code != 200:
        return []
    if 'text/html' in resp.headers.get('Content-Type', ''):
        print("Przekierowano na logowanie")
        return []
    text = resp.content.decode('utf-8', errors='replace')
    reader = csv.reader(io.StringIO(text))
    all_rows = list(reader)
    print(f"Łącznie wierszy w CSV: {len(all_rows)}")
    rows = []
    for row in all_rows:
        if len(row) >= 9 and row[2] and "202" in row[2]:
            rows.append(row)
    print(f"Wierszy z danymi: {len(rows)}")
    return rows

def compute_hash(data):
    return hashlib.md5(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def read_github_file(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]
    return None, None

def write_github_file(path, content, sha=None, message="Update"):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    payload = {"message": message, "content": base64.b64encode(content.encode()).decode()}
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=headers, json=payload)
    print(f"Write {path}: {resp.status_code}")
    return resp.status_code in [200, 201]

def main():
    print(f"[{datetime.now().isoformat()}] Pobieranie planu...")
    rows = fetch_sheet()
    if not rows:
        print("Brak danych — przerywam")
        return
    print(f"Pobrano {len(rows)} wierszy z danymi")
    new_hash = compute_hash(rows)
    old_hash_content, hash_sha = read_github_file(HASH_FILE)
    old_hash = old_hash_content.strip() if old_hash_content else ""
    if new_hash == old_hash:
        print("Brak zmian")
        return
    print("Wykryto zmiany! Aktualizuję...")
    data_payload = {"updated": datetime.now().isoformat(), "rows": rows}
    data_content = json.dumps(data_payload, ensure_ascii=False, indent=2)
    _, data_sha = read_github_file(DATA_FILE)
    ok1 = write_github_file(DATA_FILE, data_content, data_sha, f"Aktualizacja {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    ok2 = write_github_file(HASH_FILE, new_hash, hash_sha, "Hash")
    print("OK!" if ok1 and ok2 else "Błąd zapisu")

if __name__ == "__main__":
    main()
