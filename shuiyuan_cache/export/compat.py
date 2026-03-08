import concurrent.futures
import json
import os.path
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any
from collections.abc import Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shuiyuan_cache.auth.storage_state import build_cookie_header_from_storage_state
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.export.constants import (
    Shuiyuan_Topic,
    UserAgentStr,
    code_block_pagination,
    details_end_pagination,
    layer_pagination,
)

_cookie_default_path = "./cookies.txt"
_default_cache_root = "cache"


def resolve_auth_cookie_header(
    path: str = _cookie_default_path, cache_root: str = _default_cache_root
) -> str:
    config = CacheConfig(cache_root=Path(cache_root), cookie_path=Path(path))
    storage_cookie = build_cookie_header_from_storage_state(
        config.storage_state_path, config.base_url
    )
    if storage_cookie:
        return storage_cookie
    return read_cookie(path)


@cache
def read_cookie(path: str = _cookie_default_path) -> str:
    """
    阅读path为 './cookies.txt' 的文件并写入。
    如果对应的cookie不存在，则返回空字符串
    """
    if not os.path.exists(path):
        return ""
    with open(path) as file:
        return file.read()


def set_cookie(data: str, path: str = _cookie_default_path) -> None:
    read_cookie.cache_clear()
    with open(path, "w", encoding="utf-8") as file:
        file.write(data)


def validate_cookie(cookie_str):
    cookie_pattern = re.compile(r"^(?:\s*\w+\s*=\s*[^;]*;)+$")
    return cookie_pattern.match(cookie_str) is not None


@dataclass
class ReqParam:
    url: str
    headers: dict[str, str]
    retries: int = 3
    delay: int = 1

    def __init__(self, url: str):
        self.url = url
        self.headers = {
            "User-Agent": UserAgentStr,
            "Cookie": resolve_auth_cookie_header(),
        }


_url_retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=_url_retry)


def init_session():
    shuiyuan_session = requests.Session()
    shuiyuan_session.headers.update(
        {
            "User-Agent": UserAgentStr,
            "Cookie": resolve_auth_cookie_header(),
        }
    )
    shuiyuan_session.mount("http://", adapter)
    shuiyuan_session.mount("https://", adapter)
    return shuiyuan_session


_init_session, _req_session = False, None
_request_posts_cache: dict[str, Any] = {}


def make_request(param: ReqParam, once=True):
    cacheable: bool = ".json" in param.url
    if cacheable and param.url in _request_posts_cache:
        return _request_posts_cache[param.url]

    global _init_session, _req_session
    if not _init_session or _req_session is None:
        _req_session = init_session()
        _init_session = True
    if not _req_session:
        raise NotImplementedError

    def req_once():
        response = _req_session.get(param.url, headers=param.headers)
        if cacheable:
            _request_posts_cache[param.url] = response
        return response

    def req_multi():
        return req_once()

    if once:
        return req_once()
    return req_multi()


def parallel_topic_in_page(topic: str, limit: int):
    def decorator(func: Callable[[int], Any]):
        def wrapper():
            nonlocal topic
            url_json = Shuiyuan_Topic + topic + ".json"
            req_param = ReqParam(url=url_json)
            response_json = make_request(req_param, once=True)

            try:
                data = json.loads(response_json.text)
                posts_count = data["posts_count"]
                pages = posts_count // limit + (1 if posts_count % limit != 0 else 0)
            except Exception as exc:
                raise Exception(f"获取页数失败! 原因:{exc}")

            print(f"总页数 {pages}: 正在爬取......")
            result_futures = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for i in range(1, pages + 1):
                    future = executor.submit(func, i)
                    result_futures.append(future)
                print("工作已加载完毕")

            results = []
            for count, result in enumerate(
                concurrent.futures.as_completed(result_futures)
            ):
                try:
                    results.append(result.result())
                    if count % 10 == 0:
                        print(f"--- 已完成工作: {count}/{pages}")
                except Exception as exc:
                    print(f"Exception: {exc}")
            return results

        return wrapper

    return decorator


def code_block_fix(content: str) -> str:
    def find_end_pos(content: str, start: int = None, end: int = None) -> int:
        layer_pos = content.find(layer_pagination, start, end)
        details_pos = content.find(details_end_pagination, start, end)
        if layer_pos == -1 and details_pos == -1:
            return -1
        if layer_pos == -1:
            return details_pos
        if details_pos == -1:
            return layer_pos
        return min(layer_pos, details_pos)

    fixed_content = ""
    insert_pos = []
    code_block_start = 0
    while True:
        code_block_start = content.find(code_block_pagination, code_block_start)
        if code_block_start == -1:
            break
        code_block_start += 1
        code_block_end = content.find(code_block_pagination, code_block_start)
        end_pos = find_end_pos(content, start=code_block_start)
        if end_pos == -1:
            break
        if code_block_end == -1:
            insert_pos.append(end_pos)
            break
        if end_pos < code_block_end:
            insert_pos.append(end_pos)
            code_block_start = code_block_end
        elif end_pos > code_block_end:
            code_block_start = end_pos
    if not insert_pos:
        return content
    for insert_position in insert_pos:
        fixed_content += content[:insert_position] + code_block_pagination + "\n"
    fixed_content += content[insert_pos[-1] :]
    return fixed_content


def get_main_raw_post(topic: str, post: str) -> str:
    if not topic:
        return ""
    try:
        from shuiyuan_cache.export.cache_bridge import get_export_cache_bridge

        topic_id = topic[1:] if topic.startswith("L") else topic
        post_number = int(post) if post else 1
        return get_export_cache_bridge().get_post_raw(topic_id, post_number)
    except Exception:
        return ""


def add_md_quote(md_text: str) -> str:
    """
    Adds Markdown quote formatting to the given text.

    :param md_text: The Markdown text to be converted to a quote.
    :return: The quoted Markdown text.
    """
    lines = md_text.splitlines()
    quoted_lines = [f"> {line}" for line in lines]
    quoted_text = "\n".join(quoted_lines)
    return quoted_text


def quote_in_shuiyuan(md_text: str) -> str:
    """
    parse links like https://shuiyuan.sjtu.edu.cn/t/topic/XXXXX(/XXXX) to quote
    """
    code_block_pattern = r"(?P<code_block>```[\s\S]*?```|`[^`]*`)"
    markdown_link_pattern = r"\[.*?\]\(https?://[^\)]+\)"
    bare_link_pattern = r"https://shuiyuan\.sjtu\.edu\.cn/t/topic/(\d+)(/(\d+))?"

    code_blocks = re.findall(code_block_pattern, md_text)
    markdown_links = re.findall(markdown_link_pattern, md_text)

    temp_text = re.sub(code_block_pattern, "%%CODE_BLOCK%%", md_text)
    temp_text = re.sub(markdown_link_pattern, "%%MARKDOWN_LINK%%", temp_text)

    def replace(match: re.Match) -> str:
        topic = match[1]
        post = match[3]
        quote_text = get_main_raw_post(topic, post)
        return add_md_quote(quote_text)

    replaced_text = re.sub(bare_link_pattern, replace, temp_text)

    for block in code_blocks:
        replaced_text = replaced_text.replace("%%CODE_BLOCK%%", block, 1)
    for link in markdown_links:
        replaced_text = replaced_text.replace("%%MARKDOWN_LINK%%", link, 1)

    return replaced_text
