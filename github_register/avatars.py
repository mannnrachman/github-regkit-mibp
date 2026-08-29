"""Random profile avatar fetchers (DiceBear / nekos.best / waifu.im)."""
from __future__ import annotations

import io
import random
import tempfile
from pathlib import Path
from typing import Callable, Optional, Sequence
from urllib.parse import urlsplit

import requests
from PIL import Image

# nekos.best requires: APP_NAME (CONTACT_INFO) — library defaults get 403.
_USER_AGENT = "GitHubRegKit (https://github.com/mannnrachman/github-regkit-mibp)"
_HEADERS = {"User-Agent": _USER_AGENT, "Accept": "*/*"}

DEFAULT_PROVIDERS: tuple[str, ...] = ("dicebear", "nekos", "waifu_im")
_AVATAR_SIZE = 500
_MAX_BYTES = 950_000  # stay under GitHub's 1 MB hard limit

_DICEBEAR_STYLES = ("lorelei", "adventurer", "notionists", "avataaars")


class AvatarError(RuntimeError):
    """Raised when one provider fails; caller may try the next."""


def requests_proxies(proxy_url: str = "") -> Optional[dict[str, str]]:
    """Build requests proxies dict from a pool/single URL (socks → socks5h)."""
    url = (proxy_url or "").strip()
    if not url:
        return None
    p = urlsplit(url)
    if not p.hostname:
        raise AvatarError(f"invalid proxy url: {url}")
    raw_scheme = (p.scheme or "http").lower()
    if raw_scheme.startswith("socks"):
        scheme = "socks5h"
    else:
        scheme = raw_scheme if raw_scheme in ("http", "https") else "http"
    auth = f"{p.username}:{p.password}@" if p.username else ""
    port = p.port or (1080 if scheme.startswith("socks") else (443 if scheme == "https" else 80))
    endpoint = f"{scheme}://{auth}{p.hostname}:{port}"
    return {"http": endpoint, "https": endpoint}


def _session(proxy_url: str = "") -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    proxies = requests_proxies(proxy_url)
    if proxies:
        s.proxies.update(proxies)
    return s


def normalize_avatar(raw: bytes, size: int = _AVATAR_SIZE) -> bytes:
    """Center-crop to square JPEG ≈ size×size, under GitHub's 1 MB limit."""
    try:
        img = Image.open(io.BytesIO(raw))
    except Exception as exc:
        raise AvatarError(f"cannot decode image: {exc}") from exc
    img = img.convert("RGB")
    w, h = img.size
    side = min(w, h)
    if side < 64:
        raise AvatarError(f"image too small: {w}x{h}")
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    data = b""
    for quality in (90, 80, 70, 55):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= _MAX_BYTES:
            return data
    raise AvatarError(f"avatar still too large after compress: {len(data)} bytes")


def _download(url: str, session: requests.Session, timeout: int = 30) -> bytes:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.content
    if not data:
        raise AvatarError(f"empty download: {url}")
    return data


def fetch_dicebear(
    seed: str,
    session: Optional[requests.Session] = None,
    proxy_url: str = "",
) -> bytes:
    """Generate a deterministic anime-ish avatar PNG via DiceBear HTTP API."""
    s = session or _session(proxy_url)
    style = random.choice(_DICEBEAR_STYLES)
    safe_seed = requests.utils.quote(seed or f"seed{random.randint(1, 10**9)}", safe="")
    url = (
        f"https://api.dicebear.com/10.x/{style}/png"
        f"?seed={safe_seed}&size={_AVATAR_SIZE}"
    )
    return _download(url, s)


def fetch_nekos(
    session: Optional[requests.Session] = None,
    proxy_url: str = "",
) -> bytes:
    """Random SFW anime still (neko category = PNG)."""
    s = session or _session(proxy_url)
    meta = s.get("https://nekos.best/api/v2/neko", timeout=25)
    meta.raise_for_status()
    payload = meta.json()
    try:
        url = payload["results"][0]["url"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AvatarError(f"nekos.best bad payload: {exc}") from exc
    return _download(url, s)


def fetch_waifu_im(
    session: Optional[requests.Session] = None,
    proxy_url: str = "",
) -> bytes:
    """Random SFW image from waifu.im (exclude common suggestive tags)."""
    s = session or _session(proxy_url)
    meta = s.get(
        "https://api.waifu.im/images",
        params={
            "IsNsfw": "False",
            "ExcludedTags": "oppai,ass,erotic",
        },
        timeout=25,
    )
    meta.raise_for_status()
    payload = meta.json()
    items = payload.get("items") or payload.get("images") or []
    if not items:
        raise AvatarError("waifu.im returned no images")
    url = items[0].get("url")
    if not url:
        raise AvatarError("waifu.im item missing url")
    return _download(url, s)


_FETCHERS: dict[str, Callable[..., bytes]] = {
    "dicebear": fetch_dicebear,
    "nekos": fetch_nekos,
    "waifu_im": fetch_waifu_im,
}


def resolve_providers(providers: Optional[Sequence[str]] = None) -> list[str]:
    raw = list(providers) if providers else list(DEFAULT_PROVIDERS)
    out: list[str] = []
    for name in raw:
        key = (name or "").strip().lower().replace("-", "_")
        if key in ("waifu", "waifuim"):
            key = "waifu_im"
        if key in _FETCHERS and key not in out:
            out.append(key)
    return out or list(DEFAULT_PROVIDERS)


def fetch_random_avatar(
    seed: str = "",
    providers: Optional[Sequence[str]] = None,
    log: Optional[Callable[[str], None]] = None,
    proxy_url: str = "",
) -> tuple[bytes, str]:
    """Shuffle providers, try each until one yields a normalized JPEG.

    Returns (jpeg_bytes, provider_name).
    """
    order = resolve_providers(providers)
    random.shuffle(order)
    session = _session(proxy_url)
    errors: list[str] = []
    for name in order:
        try:
            if name == "dicebear":
                raw = fetch_dicebear(seed, session, proxy_url=proxy_url)
            else:
                raw = _FETCHERS[name](session, proxy_url=proxy_url)
            jpeg = normalize_avatar(raw)
            if log:
                log(f"[*] avatar bytes ready from {name} ({len(jpeg)} bytes)")
            return jpeg, name
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            if log:
                log(f"[!] avatar provider {name} failed: {exc}")
    raise AvatarError("all avatar providers failed: " + "; ".join(errors))


def write_temp_avatar(jpeg: bytes, prefix: str = "gh-avatar-") -> Path:
    """Write JPEG to a NamedTemporaryFile that survives until caller unlinks it."""
    tmp = tempfile.NamedTemporaryFile(
        prefix=prefix, suffix=".jpg", delete=False
    )
    try:
        tmp.write(jpeg)
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()
