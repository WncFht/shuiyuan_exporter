from shuiyuan_cache.export.cli_support import build_parser
from shuiyuan_cache.export.constants import default_save_dir
from shuiyuan_cache.skill_api.runtime import default_skill_export_root


def test_legacy_export_cli_imports_cleanly() -> None:
    parser = build_parser()
    args = parser.parse_args([])

    assert args.save_dir == str(default_skill_export_root())
    assert default_save_dir == str(default_skill_export_root())
