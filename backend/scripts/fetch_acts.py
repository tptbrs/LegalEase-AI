"""Download Indian Act PDFs listed in `acts_manifest.json`.

Usage (from backend/ directory):

    python -m scripts.fetch_acts             # download everything in the manifest
    python -m scripts.fetch_acts --force     # re-download even if file exists
    python -m scripts.fetch_acts --manifest path/to/manifest.json

Idempotent: skips entries whose target file already exists with non-zero size.
Validates that the response is `application/pdf` (or has %PDF header) before saving,
so a redirect to an HTML error page won't pollute `data/acts/`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from tqdm import tqdm

from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fetch_acts")

DEFAULT_MANIFEST = Path(__file__).resolve().parent / "acts_manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "LegalEaseAI/1.0 (educational research; +https://localhost)"
)


@dataclass(slots=True)
class Entry:
    act_name: str
    year: str
    domain: str
    url: str

    @property
    def filename(self) -> str:
        return f"{self.act_name}__{self.year}__{self.domain}.pdf"


def _load_manifest(path: Path) -> list[Entry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[Entry] = []
    for item in raw.get("acts", []):
        try:
            out.append(
                Entry(
                    act_name=item["act_name"].strip(),
                    year=str(item["year"]).strip(),
                    domain=item["domain"].strip().lower(),
                    url=item["url"].strip(),
                )
            )
        except KeyError as exc:
            logger.warning("Manifest entry missing field %s: %s", exc, item)
    return out


def _looks_like_pdf(content: bytes, content_type: str | None) -> bool:
    if content[:4] == b"%PDF":
        return True
    if content_type and "pdf" in content_type.lower():
        return True
    return False


def _download(client: httpx.Client, entry: Entry, dest: Path) -> tuple[bool, str]:
    try:
        with client.stream("GET", entry.url) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            total = int(resp.headers.get("content-length") or 0)
            tmp = dest.with_suffix(dest.suffix + ".part")
            chunks: list[bytes] = []
            first_chunk_seen = False
            with tmp.open("wb") as f, tqdm(
                total=total or None,
                unit="B",
                unit_scale=True,
                desc=entry.filename,
                leave=False,
            ) as bar:
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    if not first_chunk_seen:
                        chunks.append(chunk[:4])
                        first_chunk_seen = True
                    f.write(chunk)
                    bar.update(len(chunk))
            header = b"".join(chunks)[:4]
            if not _looks_like_pdf(header, content_type):
                tmp.unlink(missing_ok=True)
                return False, f"response is not a PDF (content-type={content_type!r})"
            tmp.replace(dest)
            return True, f"saved {dest.name} ({dest.stat().st_size:,} bytes)"
    except httpx.HTTPStatusError as exc:
        return False, f"HTTP {exc.response.status_code}"
    except httpx.RequestError as exc:
        return False, f"network error: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"unexpected error: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Indian Act PDFs from a manifest")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override target directory (default: backend/data/acts)",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    settings = get_settings()
    settings.ensure_dirs()
    data_dir = (args.data_dir or settings.data_dir).resolve()

    entries = _load_manifest(args.manifest)
    if not entries:
        print("Manifest contains no entries.", file=sys.stderr)
        return 1

    logger.info("Manifest: %d acts -> %s", len(entries), data_dir)

    success = 0
    skipped = 0
    failed: list[tuple[Entry, str]] = []

    timeout = httpx.Timeout(60.0, connect=15.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"}

    with httpx.Client(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
        verify=True,
    ) as client:
        for entry in entries:
            dest = data_dir / entry.filename
            if dest.exists() and dest.stat().st_size > 0 and not args.force:
                logger.info("[skip] %s already present (%d bytes)", entry.filename, dest.stat().st_size)
                skipped += 1
                continue
            logger.info("[fetch] %s <- %s", entry.filename, entry.url)
            ok, msg = _download(client, entry, dest)
            if ok:
                success += 1
                logger.info("  ok: %s", msg)
            else:
                failed.append((entry, msg))
                logger.error("  failed: %s", msg)

    print()
    print(f"Downloaded: {success}")
    print(f"Skipped (already present): {skipped}")
    if failed:
        print(f"Failed: {len(failed)}")
        for e, msg in failed:
            print(f"  - {e.filename}: {msg}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
