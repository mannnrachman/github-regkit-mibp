"""Self-check for non-network logic. Run: python -m tests.test_core"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from github_register.profiles import (
    extract_github_code,
    generate_password,
    generate_username,
    is_valid_username,
    parse_public_profile,
)


def test_extract_code():
    assert extract_github_code("Here's your GitHub verification code: 1234 5678") == "12345678"
    assert extract_github_code("Your verification code is 12345678. It expires soon.") == "12345678"
    assert extract_github_code("verification code: 9876 5432") == "98765432"
    assert extract_github_code("no code here") is None
    assert extract_github_code("") is None


def test_password():
    for _ in range(50):
        pw = generate_password()
        assert len(pw) >= 12
        assert any(c.islower() for c in pw)
        assert any(c.isupper() for c in pw)
        assert any(c.isdigit() for c in pw)


def test_username():
    for _ in range(100):
        name = generate_username()
        assert is_valid_username(name), name


def test_generate_repo_name():
    from github_register.profiles import _REPO_PROJECTS, generate_repo_name

    assert "todo-list" in _REPO_PROJECTS
    assert "portfolio" in _REPO_PROJECTS
    for _ in range(50):
        name = generate_repo_name()
        assert name in _REPO_PROJECTS, name
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), name
        assert "hex" not in name
        assert not re.search(r"-[0-9a-f]{4}$", name)


def test_generate_profile_status():
    from github_register.profiles import _PROFILE_STATUSES, generate_profile_status

    assert "On vacation" in _PROFILE_STATUSES
    assert "Focusing" in _PROFILE_STATUSES
    for _ in range(30):
        status = generate_profile_status()
        assert status in _PROFILE_STATUSES
        assert status.strip()


def test_litensi_zone_pick():
    from github_register.litensi import LitensiClient

    cli = LitensiClient("id", "key", "github", "")
    zones = [
        {"zone": "a", "stock": 0, "price": 1},
        {"zone": "b", "stock": 5, "price": 3},
        {"zone": "c", "stock": 2, "price": 1.5},
    ]
    stock = [z for z in zones if float(z.get("stock") or 0) > 0]
    assert min(stock, key=lambda z: float(z.get("price") or 0))["zone"] == "c"


def test_proxy_pool_pick():
    from github_register.config import Config
    from github_register.runner import (
        _pick_proxy_url,
        load_proxy_pool,
        normalize_proxy_line,
        proxy_display,
        proxy_endpoint,
    )

    from github_register import runner

    assert normalize_proxy_line("1.2.3.4:8080:user:pass") == "http://user:pass@1.2.3.4:8080"
    assert normalize_proxy_line("http://u:p@1.1.1.1:8080") == "http://u:p@1.1.1.1:8080"
    assert normalize_proxy_line("# comment") is None
    assert normalize_proxy_line("not a proxy") is None

    assert proxy_endpoint("http://u:secret@1.2.3.4:6754") == "1.2.3.4:6754"
    assert proxy_display("http://u:secret@1.2.3.4:6754") == "http://u:***@1.2.3.4:6754"
    assert "secret" not in proxy_display("http://u:secret@1.2.3.4:6754")

    from github_register.runner import headless_mode_label, resolve_camoufox_headless

    assert resolve_camoufox_headless(Config(headless=True, virtual_display=False)) is True
    assert resolve_camoufox_headless(Config(headless=False, virtual_display=True)) == "virtual"
    assert resolve_camoufox_headless(Config(headless=True, virtual_display=True)) == "virtual"
    assert headless_mode_label(Config(virtual_display=True)) == "virtual(Xvfb)"

    pool_name = "_test_pool_tmp.txt"
    pool_path = runner.ROOT / pool_name
    pool_path.write_text(
        "# comment\n"
        "http://u:p@1.1.1.1:8080\n"
        "\n"
        "not a proxy line\n"
        "2.2.2.2:1080:u:p\n"
        "socks5://u:p@2.2.2.2:1080\n",
        encoding="utf-8",
    )
    try:
        pool = load_proxy_pool(pool_name)
        assert pool == [
            "http://u:p@1.1.1.1:8080",
            "http://u:p@2.2.2.2:1080",
            "socks5://u:p@2.2.2.2:1080",
        ], pool
        cfg = Config(proxy="http://fallback:1@3.3.3.3:80", proxy_file=pool_name)
        assert _pick_proxy_url(cfg) in pool
        cfg2 = Config(proxy="http://fallback:1@3.3.3.3:80", proxy_file="")
        assert _pick_proxy_url(cfg2) == "http://fallback:1@3.3.3.3:80"
        cfg3 = Config(proxy="http://fallback:1@3.3.3.3:80", proxy_file="_missing_pool.txt")
        assert _pick_proxy_url(cfg3) == "http://fallback:1@3.3.3.3:80"
    finally:
        pool_path.unlink(missing_ok=True)


def test_parse_public_profile():
    random_user = {
        "results": [{
            "name": {"title": "Mr", "first": "Caleb", "last": "Harvey"},
            "location": {"country": "Ireland"},
            # These must not be included in the resulting profile data.
            "email": "caleb.harvey@example.com",
            "login": {"password": "shop"},
        }]
    }
    quote = [{"q": "A public quote."}]
    assert parse_public_profile(random_user, quote) == {
        "name": "Mr Caleb Harvey", "location": "Ireland", "bio": "A public quote.",
    }
    try:
        parse_public_profile({}, [])
    except ValueError:
        pass
    else:
        raise AssertionError("invalid profile payload must fail")


def test_avatar_normalize_and_providers():
    from PIL import Image

    from github_register.avatars import (
        normalize_avatar,
        requests_proxies,
        resolve_providers,
        write_temp_avatar,
    )

    assert resolve_providers(None) == ["dicebear", "nekos", "waifu_im"]
    assert resolve_providers(["waifu", "dicebear", "dicebear", "nope"]) == [
        "waifu_im",
        "dicebear",
    ]

    assert requests_proxies("") is None
    socks = requests_proxies("socks5://u:p@1.2.3.4:1080")
    assert socks["http"].startswith("socks5h://u:p@1.2.3.4:1080")
    http = requests_proxies("http://u:p@5.6.7.8:8080")
    assert http["https"] == "http://u:p@5.6.7.8:8080"

    buf = __import__("io").BytesIO()
    Image.new("RGB", (800, 600), color=(30, 144, 255)).save(buf, format="PNG")
    jpeg = normalize_avatar(buf.getvalue(), size=500)
    assert jpeg[:2] == b"\xff\xd8"
    assert len(jpeg) < 950_000
    img = Image.open(__import__("io").BytesIO(jpeg))
    assert img.size == (500, 500)

    path = write_temp_avatar(jpeg)
    try:
        assert path.is_file()
        assert path.stat().st_size == len(jpeg)
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        fn()
        print(f"[OK] {name}")
    print("[*] all tests passed")
