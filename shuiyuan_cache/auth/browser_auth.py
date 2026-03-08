from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Error, sync_playwright

from shuiyuan_cache.auth.storage_state import (
    build_cookie_header,
    count_domain_cookies,
    write_cookie_header,
)
from shuiyuan_cache.core.config import CacheConfig


@dataclass(slots=True)
class AuthSetupResult:
    browser: str
    base_url: str
    login_url: str
    profile_dir: str
    storage_state_path: str
    cookie_path: str
    cookie_count: int
    cookie_header_length: int
    saved_at: str


class BrowserAuthManager:
    def __init__(self, config: CacheConfig):
        self.config = config

    def setup_interactive(self, browser: str = 'edge', login_url: str | None = None, headless: bool = False) -> AuthSetupResult:
        resolved_login_url = login_url or f"{self.config.base_url.rstrip('/')}/latest"
        self.config.auth_root.mkdir(parents=True, exist_ok=True)
        self.config.browser_profile_dir.mkdir(parents=True, exist_ok=True)

        browser_type_name, channel = self._resolve_browser(browser)
        with sync_playwright() as playwright:
            browser_type = getattr(playwright, browser_type_name)
            context = browser_type.launch_persistent_context(
                user_data_dir=str(self.config.browser_profile_dir),
                channel=channel,
                headless=headless,
                viewport={'width': 1440, 'height': 960},
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(resolved_login_url, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)
                self._print_setup_instructions(browser=browser, profile_dir=self.config.browser_profile_dir, storage_state_path=self.config.storage_state_path)
                input('完成登录后请回到终端，按 Enter 保存登录态...\n')
                self._touch_forum_home(page)
                return self._save_auth_artifacts(context, browser=browser, login_url=resolved_login_url)
            finally:
                context.close()

    def refresh_from_profile(self, browser: str = 'edge', headless: bool = False) -> AuthSetupResult:
        self.config.auth_root.mkdir(parents=True, exist_ok=True)
        self.config.browser_profile_dir.mkdir(parents=True, exist_ok=True)
        browser_type_name, channel = self._resolve_browser(browser)
        with sync_playwright() as playwright:
            browser_type = getattr(playwright, browser_type_name)
            context = browser_type.launch_persistent_context(
                user_data_dir=str(self.config.browser_profile_dir),
                channel=channel,
                headless=headless,
                viewport={'width': 1440, 'height': 960},
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                self._touch_forum_home(page)
                return self._save_auth_artifacts(context, browser=browser, login_url=f"{self.config.base_url.rstrip('/')}/latest")
            finally:
                context.close()

    def auth_status(self) -> dict:
        storage_exists = self.config.storage_state_path.exists()
        cookie_exists = self.config.cookie_path.exists()
        cookie_text = self.config.cookie_path.read_text(encoding='utf-8').strip() if cookie_exists else ''
        return {
            'base_url': self.config.base_url,
            'profile_dir': str(self.config.browser_profile_dir),
            'profile_exists': self.config.browser_profile_dir.exists(),
            'storage_state_path': str(self.config.storage_state_path),
            'storage_state_exists': storage_exists,
            'storage_state_cookie_count': count_domain_cookies(self.config.storage_state_path, self.config.base_url) if storage_exists else 0,
            'cookie_path': str(self.config.cookie_path),
            'cookie_file_exists': cookie_exists,
            'cookie_header_length': len(cookie_text),
        }

    def _save_auth_artifacts(self, context: BrowserContext, browser: str, login_url: str) -> AuthSetupResult:
        context.storage_state(path=str(self.config.storage_state_path))
        cookies = context.cookies([self.config.base_url])
        base_host = urlparse(self.config.base_url).hostname or ''
        filtered_cookies = [cookie for cookie in cookies if self._domain_matches(cookie.get('domain', ''), base_host)]
        cookie_header = build_cookie_header(filtered_cookies)
        write_cookie_header(self.config.cookie_path, cookie_header)
        return AuthSetupResult(
            browser=browser,
            base_url=self.config.base_url,
            login_url=login_url,
            profile_dir=str(self.config.browser_profile_dir),
            storage_state_path=str(self.config.storage_state_path),
            cookie_path=str(self.config.cookie_path),
            cookie_count=len(filtered_cookies),
            cookie_header_length=len(cookie_header),
            saved_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )

    def _touch_forum_home(self, page) -> None:
        try:
            page.goto(f"{self.config.base_url.rstrip('/')}/latest", wait_until='domcontentloaded')
            page.wait_for_timeout(1500)
        except Error:
            pass

    @staticmethod
    def _resolve_browser(browser: str) -> tuple[str, str | None]:
        name = browser.lower().strip()
        if name == 'edge':
            return 'chromium', 'msedge'
        if name == 'chrome':
            return 'chromium', 'chrome'
        if name == 'chromium':
            return 'chromium', None
        raise ValueError(f'Unsupported browser: {browser}')

    @staticmethod
    def _domain_matches(cookie_domain: str, host: str) -> bool:
        normalized_domain = (cookie_domain or '').lstrip('.').lower()
        normalized_host = (host or '').lower()
        return normalized_domain == normalized_host or normalized_host.endswith(f'.{normalized_domain}')

    @staticmethod
    def _print_setup_instructions(browser: str, profile_dir: Path, storage_state_path: Path) -> None:
        print('已打开独立浏览器 profile，请在新窗口里完成饮水思源登录。')
        print(f'browser: {browser}')
        print(f'profile_dir: {profile_dir}')
        print(f'storage_state_path: {storage_state_path}')
        print('建议操作：先访问 https://shuiyuan.sjtu.edu.cn/latest ，确认能正常看到已登录页面。')
