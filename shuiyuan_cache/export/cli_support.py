import argparse
import cProfile
import importlib
import os
import platform
import re
from collections.abc import Sequence
from pathlib import Path
import pstats
from pstats import SortKey

from shuiyuan_cache.export.compat import resolve_auth_cookie_header, set_cookie
from shuiyuan_cache.export.constants import default_save_dir
from shuiyuan_cache.export.topic_exporter import export_topic
from shuiyuan_cache.skill_api.runtime import (
    default_skill_cache_root,
    default_skill_cookie_path,
    default_skill_runtime_root,
)


def export_input(
    save_dir: str = default_save_dir,
    cache_root: str = str(default_skill_cache_root()),
    cookie_path: str = str(default_skill_cookie_path()),
) -> None:
    topic = input('请输入帖子编号:(退出请输入"???")\n')
    if topic == "???":
        raise Exception("Exit.")
    export_topic(
        topic,
        save_dir=save_dir,
        cache_root=cache_root,
        cookie_path=cookie_path,
    )


def cookie_set(
    cookie_path: str = str(default_skill_cookie_path()),
    cache_root: str = str(default_skill_cache_root()),
) -> bool:
    while True:
        cookies = input('请输入cookie:(如果使用上次结果请输入"!!!",退出输入"???")\n')
        if cookies == "???":
            return False
        if cookies == "!!!":
            cookie_string = resolve_auth_cookie_header(
                path=cookie_path,
                cache_root=cache_root,
            )
            if cookie_string:
                return True
            print("您还未设置可用登录态！")
        elif cookies:
            set_cookie(data=cookies, path=cookie_path)
            print("已同步新cookie到文件")
            return True


def run(
    batch_topic: Sequence[str] | None = None,
    ask_cookie: bool = True,
    save_dir: str = default_save_dir,
    cache_root: str = str(default_skill_cache_root()),
    cookie_path: str = str(default_skill_cookie_path()),
) -> None:
    if ask_cookie and not cookie_set(cookie_path=cookie_path, cache_root=cache_root):
        return
    if batch_topic:
        for topic in batch_topic:
            try:
                export_topic(
                    topic=topic,
                    save_dir=save_dir,
                    cache_root=cache_root,
                    cookie_path=cookie_path,
                )
            except Exception as exc:
                print(exc)
        return

    while True:
        try:
            export_input(
                save_dir=save_dir,
                cache_root=cache_root,
                cookie_path=cookie_path,
            )
        except Exception as exc:
            print(exc)
            break


def clean(directory: Path = Path(default_save_dir)) -> None:
    if not directory.exists():
        print(f"目录不存在: {directory}")
        return

    def clean_helper(item: Path) -> None:
        if item.is_dir() and re.match(r"\d+", item.name):
            print(f"目录: {item}")
            for file in item.iterdir():
                if file.name.endswith("Empty.md") or file.name.endswith(
                    "Single Sign On.md"
                ):
                    os.remove(file)

    for item in directory.iterdir():
        if item.is_dir() and not re.match(r"\d+", item.name):
            clean(directory=item)
        elif item.is_dir():
            clean_helper(item)


def stat(program: str) -> None:
    stat_dir = default_skill_runtime_root() / "stat"
    stat_dir.mkdir(parents=True, exist_ok=True)
    cProfile.run(program, str(stat_dir / "run_stats.txt"))
    stats = pstats.Stats(str(stat_dir / "run_stats.txt"))
    stats.strip_dirs().sort_stats(SortKey.TIME).print_stats(10)


def detect_os() -> str:
    os_name = platform.system()
    if os_name == "Windows":
        return "Windows"
    if os_name == "Linux":
        return "Linux"
    if os_name == "Darwin":
        return "macOS"
    raise NotImplementedError(f"Unsupported OS: {os_name}")


def choose_list() -> tuple[str, list]:
    quality_list_module = importlib.import_module("shuiyuan_cache.export.quality_list")
    lists_only = {
        key: value
        for key, value in vars(quality_list_module).items()
        if isinstance(value, list) and not key.startswith("__")
    }
    list_names = list(lists_only.keys())
    host_os = detect_os()
    if host_os in ["Linux", "macOS"]:
        from simple_term_menu import TerminalMenu

        terminal_menu = TerminalMenu(list_names)
        menu_entry_index = terminal_menu.show()
        return list_names[menu_entry_index], lists_only[list_names[menu_entry_index]]
    if host_os == "Windows":
        import dumb_menu

        index = dumb_menu.get_menu_choice(list_names)
        return list_names[index], lists_only[list_names[index]]
    raise NotImplementedError(f"Unsupported OS: {host_os}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Legacy interactive export CLI. Prefer scripts/export_topic.py or "
            "scripts/ensure_cached.py for the current cache-first workflow."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-b",
        "--batch",
        nargs="+",
        type=str,
        help="For test and CI: -b 1 2 3 means download the topic 1, 2, 3",
    )
    parser.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="clean the export folder for possible meaningless md",
    )
    parser.add_argument(
        "-n",
        "--not_ask_cookie",
        action="store_true",
        help="if ask for cookie or use saved cookie directly",
    )
    parser.add_argument(
        "-s",
        "--stat",
        action="store_true",
        help="stat the time consuming analysis and save.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list the available quality list and pull one in batch mode.",
    )
    parser.add_argument(
        "--save-dir",
        default=default_save_dir,
        help="Legacy export output root",
    )
    parser.add_argument(
        "--cache-root",
        default=str(default_skill_cache_root()),
        help="Cache root used by the export bridge",
    )
    parser.add_argument(
        "--cookie-path",
        default=str(default_skill_cookie_path()),
        help="Cookie file path used as auth fallback",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ask = not args.not_ask_cookie
    if args.list:
        name, selected_list = choose_list()
        save_dir = f"{args.save_dir}/{name}"
        os.makedirs(save_dir, exist_ok=True)
        run(
            selected_list,
            ask_cookie=ask,
            save_dir=save_dir,
            cache_root=args.cache_root,
            cookie_path=args.cookie_path,
        )
        return 0
    if args.batch:
        run(
            args.batch,
            ask_cookie=ask,
            save_dir=args.save_dir,
            cache_root=args.cache_root,
            cookie_path=args.cookie_path,
        )
    elif args.clean:
        clean(Path(args.save_dir))
    elif args.stat:
        stat("run(['276006'], False)")
    else:
        run(
            ask_cookie=ask,
            save_dir=args.save_dir,
            cache_root=args.cache_root,
            cookie_path=args.cookie_path,
        )
    return 0
