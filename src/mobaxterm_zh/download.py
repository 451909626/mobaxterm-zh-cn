"""Retrieve the exact official input needed by a complete release build."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
from urllib.parse import urlparse

from .patcher import load_spec


def download_upstream(repo, upstream_version, directory):
    version, _, _ = load_spec(repo, upstream_version)
    url = urlparse(version["official_archive_url"])
    if url.scheme != "https" or url.hostname != "download.mobatek.net":
        raise ValueError("Expected the pinned official HTTPS download")
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / Path(url.path).name
    def verify(path):
        if hashlib.sha256(path.read_bytes()).hexdigest() != version["archive_sha256"]:
            raise ValueError("Official archive SHA-256 mismatch")
    if target.exists():
        verify(target)
        return target
    with tempfile.TemporaryDirectory(prefix="moba-download-", dir=directory) as temporary:
        candidate = Path(temporary) / target.name
        subprocess.run(["curl.exe", "--fail", "--location", "--retry", "3", "--output", str(candidate),
                        "--url", version["official_archive_url"]], check=True, timeout=240)
        verify(candidate)
        if candidate.resolve().parent.parent != directory or target.exists():
            raise FileExistsError("Download destination changed; existing file is preserved")
        candidate.rename(target)
    return target
