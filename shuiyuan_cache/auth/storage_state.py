import json
from pathlib import Path
from urllib.parse import urlparse


def load_storage_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def extract_domain_cookies(path: Path, base_url: str) -> list[dict]:
    payload = load_storage_state(path)
    cookies = payload.get('cookies') or []
    host = urlparse(base_url).hostname or ''
    return [cookie for cookie in cookies if _domain_matches(cookie.get('domain', ''), host)]


def build_cookie_header_from_storage_state(path: Path, base_url: str) -> str:
    cookies = extract_domain_cookies(path, base_url)
    return build_cookie_header(cookies)


def build_cookie_header(cookies: list[dict]) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for cookie in cookies:
        name = cookie.get('name')
        value = cookie.get('value')
        if not name:
            continue
        pair = f'{name}={value}'
        if pair in seen:
            continue
        parts.append(pair)
        seen.add(pair)
    return '; '.join(parts)


def write_cookie_header(path: Path, cookie_header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cookie_header.strip(), encoding='utf-8')


def count_domain_cookies(path: Path, base_url: str) -> int:
    return len(extract_domain_cookies(path, base_url))


def _domain_matches(cookie_domain: str, host: str) -> bool:
    normalized_domain = (cookie_domain or '').lstrip('.').lower()
    normalized_host = (host or '').lower()
    return normalized_domain == normalized_host or normalized_host.endswith(f'.{normalized_domain}')
