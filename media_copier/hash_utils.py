from hashlib import sha256
from pathlib import Path


HASH_CHUNK_SIZE = 16 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def files_match_sha256(source: Path, destination: Path) -> bool:
    return sha256_file(source) == sha256_file(destination)
