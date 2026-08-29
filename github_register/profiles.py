"""Profile helpers: passwords, GitHub usernames, OTP extraction."""
from __future__ import annotations

import re
import secrets
import string
from typing import Any

_LOWER = string.ascii_lowercase
_UPPER = string.ascii_uppercase
_DIGITS = string.digits
_SYMBOLS = "!@#$%^&*"

_WORDS = [
    "novak", "rava", "kelby", "orin", "zephyr", "marlow", "quill", "sable",
    "tenzin", "fable", "gable", "harlow", "irwin", "jasper", "keaton",
    "landry", "moss", "nolan", "otter", "pascal", "quinn", "rivers", "silas",
    "tobin", "ulric", "vance", "wren", "xander", "yates", "zane",
]

# Realistic first-repo names — look like small human side projects, not bot slugs.
_REPO_PROJECTS = [
    "todo-list",
    "habit-tracker",
    "expense-tracker",
    "markdown-notes",
    "daily-journal",
    "bookmark-manager",
    "url-shortener",
    "weather-cli",
    "pomodoro-timer",
    "simple-calculator",
    "password-generator",
    "file-renamer",
    "image-converter",
    "csv-cleaner",
    "json-formatter",
    "link-board",
    "reading-list",
    "flashcards",
    "quiz-app",
    "recipe-book",
    "workout-log",
    "budget-sheet",
    "time-tracker",
    "snippet-vault",
    "dotfiles",
    "portfolio",
    "landing-page",
    "blog-starter",
    "api-playground",
    "hello-world",
    "learning-python",
    "learning-go",
    "rust-exercises",
    "js-utils",
    "css-experiments",
    "react-sandbox",
    "node-scripts",
    "shell-helpers",
    "git-cheatsheet",
    "study-notes",
    "interview-prep",
    "leetcode-notes",
    "side-project",
    "weekend-build",
    "mini-blog",
    "static-site",
    "personal-site",
    "scratchpad",
    "misc-scripts",
    "tools",
]

_PROFILE_STATUSES = [
    "Focusing",
    "On vacation",
    "Out of office",
    "Working from home",
    "In a meeting",
    "Taking a break",
    "Busy",
    "Available",
    "Learning something new",
    "Shipping code",
    "Reading docs",
    "Deep work",
    "AFK for a bit",
    "Back soon",
    "Catching up on PRs",
]

_USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?!-))*[a-z0-9]$")


def generate_password(length: int = 16) -> str:
    """Random password that clears GitHub's strength/blocklist checks."""
    charset = _LOWER + _UPPER + _DIGITS + _SYMBOLS
    while True:
        pw = "".join(secrets.choice(charset) for _ in range(length))
        if (
            any(c in _LOWER for c in pw)
            and any(c in _UPPER for c in pw)
            and any(c in _DIGITS for c in pw)
        ):
            return pw


def generate_username() -> str:
    """GitHub-safe username: [a-z0-9-], no consecutive hyphens, <= 39 chars."""
    suffix = "".join(secrets.choice(_LOWER + _DIGITS) for _ in range(6))
    return f"{secrets.choice(_WORDS)}{suffix}"


def generate_repo_name() -> str:
    """Pick a plain project slug that looks like a normal first GitHub repo."""
    return secrets.choice(_REPO_PROJECTS)


_README_TAGLINES = [
    "Small personal project I use day to day.",
    "Scratch space while learning and experimenting.",
    "Tiny utility — expect rough edges.",
    "Weekend build; docs may lag behind the code.",
    "Notes and helpers collected in one place.",
    "Practice repo — structure will change.",
    "Simple tools without heavy dependencies.",
    "Work-in-progress. Feedback welcome.",
]

_README_FEATURES = [
    "Keeps a short local config",
    "CLI-friendly defaults",
    "No external account required",
    "Works offline once set up",
    "Easy to fork and tweak",
    "Minimal dependencies",
    "Readable source layout",
    "Basic error messages",
    "Sample data included",
    "Simple test commands",
]

_README_STACKS = [
    "Python 3",
    "Node.js",
    "Bash",
    "TypeScript",
    "Go",
    "Rust",
    "plain HTML/CSS",
    "Make + shell",
]

_README_GETTING_STARTED = [
    "Clone the repo and skim the files before running anything.",
    "Install dependencies for your stack, then try the sample command below.",
    "Copy any example config, edit paths, and run from the project root.",
    "Open the main script and adjust constants for your machine.",
]


def generate_repo_readme(repo_name: str) -> str:
    """Unique-looking README body so a new repo does not look empty/identical."""
    import datetime as _dt

    title = (repo_name or "project").replace("-", " ").replace("_", " ").strip().title()
    tagline = secrets.choice(_README_TAGLINES)
    features = secrets.SystemRandom().sample(_README_FEATURES, k=secrets.choice((3, 4, 5)))
    stacks = secrets.SystemRandom().sample(_README_STACKS, k=secrets.choice((2, 3)))
    started = secrets.choice(_README_GETTING_STARTED)
    year = _dt.datetime.now().year
    feature_lines = "\n".join(f"- {f}" for f in features)
    stack_lines = ", ".join(stacks)
    cmd = secrets.choice(
        (
            "python main.py --help",
            "npm start",
            "./run.sh",
            "make demo",
            "go run .",
        )
    )
    license_note = secrets.choice(
        (
            "Personal use for now — license TBD.",
            "MIT when I get around to adding a LICENSE file.",
            "Use freely; no warranty.",
        )
    )
    return (
        f"# {title}\n\n"
        f"{tagline}\n\n"
        f"## Features\n\n"
        f"{feature_lines}\n\n"
        f"## Stack\n\n"
        f"{stack_lines}\n\n"
        f"## Getting started\n\n"
        f"{started}\n\n"
        f"```bash\n"
        f"{cmd}\n"
        f"```\n\n"
        f"## Notes\n\n"
        f"- Repo name: `{repo_name}`\n"
        f"- Started around {year}\n"
        f"- {license_note}\n"
    )


def generate_profile_status() -> str:
    """Pick a normal GitHub status message (not always On vacation)."""
    return secrets.choice(_PROFILE_STATUSES)


def username_from_email(email: str, suffix: str = "") -> str:
    """Derive a GitHub username from the mailbox local-part.

    myname123@mail.example.com -> 'myname123'
    Falls back to a random username when the local-part is unusable.
    A short random suffix can be appended when the name is taken.
    """
    local = (email or "").split("@", 1)[0].strip().lower()
    local = re.sub(r"[^a-z0-9-]", "", local)
    local = local.strip("-").replace("--", "-")
    if not is_valid_username(local):
        return generate_username()
    name = (local + suffix)[:39]
    return name if is_valid_username(name) else generate_username()


def is_valid_username(name: str) -> bool:
    return 1 <= len(name) <= 39 and bool(_USERNAME_RE.match(name))


def extract_github_code(text: str) -> str | None:
    """8-digit GitHub code; the email body may separate the halves with a space."""
    if not text:
        return None
    m = re.search(r"\b(\d{4})\s*(\d{4})\b", text)
    if m:
        return m.group(1) + m.group(2)
    for pat in (
        r"verification\s+code[:\s]+(\d{4,8})",
        r"your\s+code[:\s]+(\d{4,8})",
        r"enter\s+this\s+code[:\s]+(\d{4,8})",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def parse_public_profile(random_user: Any, quote: Any) -> dict[str, str]:
    """Extract public display fields from Random User and ZenQuotes payloads.

    Contact details and generated credentials in the Random User response are
    intentionally ignored.
    """
    try:
        user = random_user["results"][0]
        person = user["name"]
        full_name = " ".join(
            part.strip()
            for part in (person.get("title", ""), person["first"], person["last"])
            if part.strip()
        )
        location = str(user["location"]["country"]).strip()
        bio = str(quote[0]["q"]).strip()
    except (IndexError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"invalid public profile payload: {exc}") from exc
    if not full_name or not location or not bio:
        raise ValueError("public profile payload has an empty required field")
    return {"name": full_name, "location": location, "bio": bio}
