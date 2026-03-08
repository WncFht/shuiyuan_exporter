from __future__ import annotations

__all__ = ["ShuiyuanSkillAPI"]


def __getattr__(name: str):
    if name == "ShuiyuanSkillAPI":
        from shuiyuan_cache.skill_api.api import ShuiyuanSkillAPI

        return ShuiyuanSkillAPI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
