import os
import sys
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
LINKS_FILE = BASE_DIR / "links.md"
OUTPUT_DIR = BASE_DIR / "advanced stats"
LAST_SYNC_FILE = BASE_DIR / ".last_sync"
SOURCE_REPO = "griffisben/Post_Match_App"


def load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def parse_links():
    links = []
    with open(LINKS_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("https://github.com/"):
                links.append(line)
    return links


def to_raw_url(blob_url):
    return blob_url.replace(
        "https://github.com/", "https://raw.githubusercontent.com/"
    ).replace("/blob/", "/")


def to_filename(blob_url):
    return unquote(blob_url.split("/")[-1])


def check_new_commits(token=None):
    last_sync = ""
    if LAST_SYNC_FILE.exists():
        with open(LAST_SYNC_FILE) as f:
            last_sync = f.read().strip()

    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    resp = requests.get(
        f"https://api.github.com/repos/{SOURCE_REPO}/commits",
        params={"path": "Stat_Files", "per_page": 1},
        headers=headers,
    )
    resp.raise_for_status()
    commits = resp.json()
    if not commits:
        return False

    latest = commits[0]["commit"]["committer"]["date"]
    if not last_sync:
        return True
    return latest > last_sync


def download_csvs(links):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for link in links:
        raw_url = to_raw_url(link)
        filename = to_filename(link)
        filepath = OUTPUT_DIR / filename

        resp = requests.get(raw_url)
        if resp.status_code != 200:
            print(f"ERRO: Falha ao descarregar {filename} ({resp.status_code})")
            continue

        with open(filepath, "wb") as f:
            f.write(resp.content)

        downloaded.append(filename)
        print(f"OK: {filename}")

    return downloaded


def git_cmd(args, cwd=None):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd or str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr:
        print(f"Git: {result.stderr.strip()}")
    return result


def commit_and_push(env):
    token = env["GITHUB_TOKEN"]
    repo = env["GITHUB_REPO"]
    user_name = env["GIT_USER_NAME"]
    user_email = env["GIT_USER_EMAIL"]

    remote_with_token = f"https://{token}@github.com/{repo}.git"
    remote_public = f"https://github.com/{repo}.git"

    git_cmd(["config", "user.name", user_name])
    git_cmd(["config", "user.email", user_email])
    git_cmd(["remote", "set-url", "origin", remote_with_token])
    git_cmd(["add", "advanced stats/"])

    result = git_cmd(["diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("Sem alteracoes para commit.")
        git_cmd(["remote", "set-url", "origin", remote_public])
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    git_cmd(["commit", "-m", f"Sync stats - {timestamp}"])
    git_cmd(["push", "origin", "HEAD"])
    git_cmd(["remote", "set-url", "origin", remote_public])

    print("Alteracoes enviadas para o repositorio.")
    return True


def save_last_sync(token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    resp = requests.get(
        f"https://api.github.com/repos/{SOURCE_REPO}/commits",
        params={"path": "Stat_Files", "per_page": 1},
        headers=headers,
    )
    if resp.status_code == 200 and resp.json():
        date = resp.json()[0]["commit"]["committer"]["date"]
        with open(LAST_SYNC_FILE, "w") as f:
            f.write(date)


def main():
    if not ENV_FILE.exists():
        print("ERRO: Ficheiro .env nao encontrado.")
        sys.exit(1)

    if not LINKS_FILE.exists():
        print("ERRO: Ficheiro links.md nao encontrado.")
        sys.exit(1)

    env = load_env()
    links = parse_links()

    if not links:
        print("ERRO: Nenhum link encontrado em links.md")
        sys.exit(1)

    token = env.get("GITHUB_TOKEN", "")

    if not check_new_commits(token):
        print("Sem novos commits no repositorio original. Nada para sincronizar.")
        sys.exit(0)

    print(f"A descarregar {len(links)} ficheiros CSV...")
    download_csvs(links)
    save_last_sync(token)
    commit_and_push(env)


if __name__ == "__main__":
    main()