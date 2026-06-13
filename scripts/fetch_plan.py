import requests
import json
import hashlib
import os
import base64
from datetime import datetime
from bs4 import BeautifulSoup

SHEET_URL = "https://docs.google.com/spreadsheets/d/1YeDuROB0ghVP0vluJi1yWNOogJSwtIsC/htmlview"
DATA_FILE = "data.json"
HASH_FILE = "data_hash.txt"
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

def fetch_sheet():
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(SHEET_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = []
    table = soup.find("table")
    if not table:
        print("Brak tabeli")
        return []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) >= 9 and cells[1] and "202" in cells[1]:
            rows.append(cells)
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
    return resp.status_code in [200, 201]

def main():
    print(f"[{datetime.now().isoformat()}] Pobieranie planu...")
    rows = fetch_sheet()
    if not rows:
        print("Brak danych")
        return
    print(f"Pobrano {len(rows)} wierszy")
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
    ok2 = write_github_file(HASH_FILE, new_hash, hash_sha, "Aktualizacja hash")
    print("OK!" if ok1 and ok2 else "Błąd zapisu")

if __name__ == "__main__":
    main()
