import json
import re
from pathlib import Path
from typing import Tuple

from shuiyuan_cache.export.compat import ReqParam, code_block_fix, make_request, parallel_topic_in_page, quote_in_shuiyuan
from shuiyuan_cache.export.constants import Shuiyuan_Raw, Shuiyuan_Topic_Json, raw_limit


def normalize_topic_id(topic: str | int) -> str:
    topic_text = str(topic)
    return topic_text[1:] if topic_text.startswith('L') else topic_text


def build_markdown_filename(topic_id: str, title: str) -> str:
    safe_title = (str(title) + '.md').replace('/', ' or ')
    safe_title = re.sub(r'[\\/*?:"<>|]', '_', safe_title)
    return f'{topic_id} {safe_title}'


def export_raw_post(output_dir: str | Path, topic: str | int) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    topic_id = normalize_topic_id(topic)

    url_json = Shuiyuan_Topic_Json + topic_id + '.json'
    response_json = make_request(param=ReqParam(url_json), once=False)
    title = 'Empty'
    if response_json.status_code == 200:
        data = json.loads(response_json.text)
        title = data['title']

    filename = build_markdown_filename(topic_id, title)
    output_path = output_dir / filename
    output_path.write_text('', encoding='utf-8')

    @parallel_topic_in_page(topic=topic_id, limit=raw_limit)
    def handle_func(page_no: int) -> Tuple[int, str]:
        url_raw = Shuiyuan_Raw + topic_id + '?page=' + str(page_no)
        response_raw = make_request(param=ReqParam(url_raw), once=False)
        if response_raw.status_code == 200:
            return page_no, quote_in_shuiyuan(code_block_fix(response_raw.text))
        return page_no, ''

    ordered_results = sorted(handle_func(), key=lambda item: item[0])
    output_path.write_text('\n'.join(text for _, text in ordered_results), encoding='utf-8')
    return filename
