"""File storage for projects, memory and the community: the local disk or a GitHub repository.

LocalStore   a folder on this computer (default; also Claude Code reads it directly)
GitHubStore  a folder in a GitHub repository via the contents API – free cloud storage that the website and the
             Mac share.  Needs a token with "Contents: read and write" for that repository.

Paths are relative, '/'-separated, and may not leave the store ('..', absolute paths are refused).
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

import requests

SAFE = re.compile(r"^[\w.\- ]{1,80}$")


def clean(path: str) -> str:
    parts = [p for p in str(path).replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts or any(p == ".." or not SAFE.match(p) for p in parts):
        raise SystemExit(f"Ungültiger Dateiname '{path}' (erlaubt: Buchstaben, Ziffern, - _ . und Leerzeichen)")
    return "/".join(parts)


class LocalStore:
    kind = "lokal"

    def __init__(self, root: Path):
        self.root = Path(root)

    def _p(self, path: str) -> Path:
        return self.root / clean(path)

    def list(self, prefix: str = "") -> list[str]:
        base = self.root / clean(prefix) if prefix else self.root
        if not base.exists():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in base.rglob("*") if p.is_file() and p.name != ".DS_Store")

    def exists(self, path: str) -> bool:
        return self._p(path).is_file()

    def read_bytes(self, path: str) -> bytes | None:
        p = self._p(path)
        return p.read_bytes() if p.is_file() else None

    def read(self, path: str) -> str | None:
        b = self.read_bytes(path)
        return None if b is None else b.decode("utf-8", errors="replace")

    def write(self, path: str, data: str | bytes, message: str = "") -> None:
        p = self._p(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)

    def delete(self, path: str, message: str = "") -> None:
        p = self._p(path)
        if p.is_file():
            p.unlink()


class GitHubStore:
    kind = "github"
    API = "https://api.github.com"

    def __init__(self, repo: str, token: str, prefix: str = "", branch: str = "main"):
        self.repo, self.prefix, self.branch = repo, prefix.strip("/"), branch
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})
        self._tree: dict[str, str] | None = None            # path -> blob sha, refreshed after every write

    def _full(self, path: str) -> str:
        return f"{self.prefix}/{clean(path)}" if self.prefix else clean(path)

    def _files(self) -> dict[str, str]:
        if self._tree is None:
            r = self.s.get(f"{self.API}/repos/{self.repo}/git/trees/{self.branch}", params={"recursive": "1"}, timeout=30)
            if r.status_code == 409:                          # empty repository
                self._tree = {}
                return self._tree
            r.raise_for_status()
            self._tree = {t["path"]: t["sha"] for t in r.json().get("tree", []) if t["type"] == "blob"}
        return self._tree

    def list(self, prefix: str = "") -> list[str]:
        base = self._full(prefix) + "/" if prefix else (self.prefix + "/" if self.prefix else "")
        cut = len(self.prefix) + 1 if self.prefix else 0
        return sorted(p[cut:] for p in self._files() if p.startswith(base))

    def exists(self, path: str) -> bool:
        return self._full(path) in self._files()

    def read_bytes(self, path: str) -> bytes | None:
        full = self._full(path)
        if full not in self._files():
            return None
        r = self.s.get(f"{self.API}/repos/{self.repo}/git/blobs/{self._files()[full]}", timeout=30)
        r.raise_for_status()
        return base64.b64decode(r.json()["content"])

    def read(self, path: str) -> str | None:
        b = self.read_bytes(path)
        return None if b is None else b.decode("utf-8", errors="replace")

    def write(self, path: str, data: str | bytes, message: str = "") -> None:
        full = self._full(path)
        raw = data.encode("utf-8") if isinstance(data, str) else data
        body = {"message": message or f"update {full}", "content": base64.b64encode(raw).decode(), "branch": self.branch}
        if full in self._files():
            body["sha"] = self._files()[full]
        r = self.s.put(f"{self.API}/repos/{self.repo}/contents/{full}", json=body, timeout=60)
        r.raise_for_status()
        self._tree = None

    def delete(self, path: str, message: str = "") -> None:
        full = self._full(path)
        if full not in self._files():
            return
        r = self.s.delete(f"{self.API}/repos/{self.repo}/contents/{full}", timeout=60,
                          json={"message": message or f"delete {full}", "sha": self._files()[full], "branch": self.branch})
        r.raise_for_status()
        self._tree = None
