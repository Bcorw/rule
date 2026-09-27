#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从单个 Sub-Store collection/JC sing-box 订阅生成 N60Pro sing-box 1.15 配置。

默认：
  订阅：
    http://127.0.0.1:3001/password/download/collection/JC?target=sing-box

  模板：
    n60pro-singbox-1.15-alpha9.json

  输出：
    config.json

逻辑：
  1. 拉取 Sub-Store sing-box JSON。
  2. 仅保留实际代理节点，按 tag 去重。
  3. 写入模板 outbounds。
  4. 按关键词生成：
       日本手动 / 狮城手动 / 香港手动 / 美国手动
       AI手动 / 流媒体手动 / 低倍率手动
       手动选择 / 自动选择
  5. 按用户指定的 selector 结构重写业务 selector，并设置 default。
  6. 自动补齐模板中缺失的辅助 selector/urltest，避免悬空引用。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SUB_URL = (
    "http://127.0.0.1:3001/"
    "password/download/collection/JC?target=sing-box"
)
DEFAULT_TEMPLATE = "n60pro-singbox-1.15-alpha9.json"
DEFAULT_OUTPUT = "config.json"


# -----------------------------------------------------------------------------
# 你指定的业务 selector 结构
# -----------------------------------------------------------------------------
# 顺序和 default 均按用户提供的版本固定，不再由模板原内容自动猜测。
SELECTOR_DEFINITIONS: dict[str, dict[str, Any]] = {
    "默认代理": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "流媒体手动",
            "低倍率手动",
            "自动选择",
        ],
        "default": "狮城手动",
    },
    "AI": {
        "outbounds": [
            "AI手动",
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "自动选择",
        ],
        "default": "AI手动",
    },
    "YouTube": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "流媒体手动",
            "低倍率手动",
            "自动选择",
        ],
        "default": "流媒体手动",
    },
    "Google": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "自动选择",
        ],
        "default": "狮城手动",
    },
    "Github": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "流媒体手动",
            "低倍率手动",
            "自动选择",
        ],
        "default": "低倍率手动",
    },
    "Telegram": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "流媒体手动",
            "低倍率手动",
            "自动选择",
        ],
        "default": "流媒体手动",
    },
    "TikTok": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "流媒体手动",
        ],
        "default": "流媒体手动",
    },
    "Netflix": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "流媒体手动",
        ],
        "default": "流媒体手动",
    },
    "Wallet": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "自动选择",
        ],
        "default": "香港手动",
    },
    "Steam": {
        "outbounds": [
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "手动选择",
            "低倍率手动",
            "直连",
        ],
        "default": "香港手动",
    },
    "Microsoft": {
        "outbounds": ["默认代理", "低倍率手动", "直连"],
        "default": "直连",
    },
    "OneDrive": {
        "outbounds": ["默认代理", "低倍率手动", "直连"],
        "default": "直连",
    },
    "Apple": {
        "outbounds": ["默认代理", "直连"],
        "default": "直连",
    },
    "漏网之鱼": {
        "outbounds": [
            "默认代理",
            "日本手动",
            "狮城手动",
            "香港手动",
            "美国手动",
            "流媒体手动",
            "低倍率手动",
            "手动选择",
            "自动选择",
            "直连",
        ],
        "default": "低倍率手动",
    },
}


# -----------------------------------------------------------------------------
# 节点分类关键词
# -----------------------------------------------------------------------------
# 关键词采用“子串匹配”，不区分英文大小写。
GROUP_FILTERS: dict[str, list[str]] = {
    "香港手动": [
        "港",
        "hk",
        "hong kong",
        "hongkong",
        "xianggang",
        "香江",
    ],
    "日本手动": [
        "日",
        "jp",
        "japan",
        "东京",
        "大阪",
        "东京",
    ],
    "狮城手动": [
        "新",
        "sg",
        "singapore",
        "狮城",
    ],
    "美国手动": [
        "美",
        "us",
        "usa",
        "united states",
        "西美",
        "洛杉矶",
        "los angeles",
        "san jose",
        "seattle",
    ],
    "AI手动": [
        "通用",
        "住宅",
        "ai",
        "openai",
        "chatgpt",
        "claude",
        "gemini",
        "gpt",
        "anthropic",
    ],
    "流媒体手动": [
        "流媒体",
        "媒体",
        "住宅ip",
        "residential",
        "netflix",
        "disney",
        "disney+",
        "hbo",
        "max",
        "prime",
        "stream",
    ],
    "低倍率手动": [
        "0.01倍",
        "0.05倍",
        "0.1倍",
        "0.2倍",
        "0.5倍",
        "0.01x",
        "0.05x",
        "0.1x",
        "0.2x",
        "0.5x",
    ],
}


# Sub-Store 可能返回一些非实际代理节点的 outbound 类型。
# 这些属于结构型 outbound，不写进订阅节点区。
STRUCTURAL_OUTBOUND_TYPES = {
    "selector",
    "urltest",
    "direct",
    "block",
    "dns",
    "dns-rule",
}


# -----------------------------------------------------------------------------
# HTTP / JSON
# -----------------------------------------------------------------------------
def fetch_nodes(url: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "sing-box-merge-config/1.15",
            "Accept": "application/json,text/plain,*/*",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"!! 拉取订阅失败: HTTP {exc.code} {exc.reason}\nURL: {url}"
        )
    except urllib.error.URLError as exc:
        raise SystemExit(f"!! 拉取订阅失败: {exc.reason}\nURL: {url}")
    except Exception as exc:
        raise SystemExit(f"!! 拉取订阅失败: {exc}\nURL: {url}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "!! Sub-Store 返回的内容不是合法 JSON。\n"
            f"URL: {url}\n"
            f"JSON 错误: {exc}\n"
            f"前 300 字符: {raw[:300]!r}"
        )

    if isinstance(data, dict) and isinstance(data.get("outbounds"), list):
        data = data["outbounds"]

    if not isinstance(data, list):
        raise SystemExit(
            "!! Sub-Store 返回的数据不是 outbounds 数组。\n"
            f"实际类型: {type(data).__name__}"
        )

    return [x for x in data if isinstance(x, dict)]


# -----------------------------------------------------------------------------
# 节点清洗
# -----------------------------------------------------------------------------
def clean_nodes(raw_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """保留实际代理节点，按 tag 去重。"""
    result: list[dict[str, Any]] = []
    seen_tags: set[str] = set()

    for node in raw_nodes:
        tag = node.get("tag")
        node_type = node.get("type")

        if not isinstance(tag, str) or not tag.strip():
            continue

        if node_type in STRUCTURAL_OUTBOUND_TYPES:
            continue

        if tag in seen_tags:
            continue

        seen_tags.add(tag)
        result.append(node)

    return result


# -----------------------------------------------------------------------------
# Template 操作
# -----------------------------------------------------------------------------
def find_outbound(config: dict[str, Any], tag: str) -> dict[str, Any] | None:
    for outbound in config.get("outbounds", []):
        if outbound.get("tag") == tag:
            return outbound
    return None


def ensure_selector(
    config: dict[str, Any],
    tag: str,
    outbounds: list[str],
    default: str | None = None,
) -> dict[str, Any]:
    """确保 selector 存在，不存在就创建。"""
    outbound = find_outbound(config, tag)
    if outbound is None:
        outbound = {
            "tag": tag,
            "type": "selector",
            "outbounds": [],
        }
        config.setdefault("outbounds", []).append(outbound)

    outbound["type"] = "selector"
    outbound["outbounds"] = list(outbounds)

    if default is not None:
        outbound["default"] = default

    return outbound


def ensure_urltest(
    config: dict[str, Any],
    tag: str,
    outbounds: list[str],
    *,
    url: str = "https://www.gstatic.com/generate_204",
    interval: str = "5m",
    tolerance: int = 50,
) -> dict[str, Any]:
    """确保 urltest 存在。"""
    outbound = find_outbound(config, tag)
    if outbound is None:
        outbound = {
            "tag": tag,
            "type": "urltest",
            "outbounds": [],
        }
        config.setdefault("outbounds", []).append(outbound)

    outbound["type"] = "urltest"
    outbound["outbounds"] = list(outbounds)
    outbound["url"] = url
    outbound["interval"] = interval
    outbound["tolerance"] = tolerance
    return outbound


def strip_old_subscription_nodes(
    config: dict[str, Any],
    new_node_tags: set[str],
) -> None:
    """删除模板中与本次订阅重复的旧节点，防止生成多次后重复。"""
    outbounds = config.setdefault("outbounds", [])
    outbounds[:] = [
        ob
        for ob in outbounds
        if not (
            isinstance(ob, dict)
            and isinstance(ob.get("tag"), str)
            and ob.get("tag") in new_node_tags
        )
    ]


def append_nodes(config: dict[str, Any], nodes: list[dict[str, Any]]) -> None:
    config.setdefault("outbounds", []).extend(nodes)


# -----------------------------------------------------------------------------
# 分类
# -----------------------------------------------------------------------------
def match_keywords(tags: list[str], keywords: list[str]) -> list[str]:
    lowered = [(tag, tag.casefold()) for tag in tags]
    result: list[str] = []

    normalized_keywords = [kw.casefold() for kw in keywords]
    for original, value in lowered:
        if any(keyword in value for keyword in normalized_keywords):
            result.append(original)

    return result


def classify(tags: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for group_name, keywords in GROUP_FILTERS.items():
        groups[group_name] = match_keywords(tags, keywords)
    return groups


def require_matches(
    groups: dict[str, list[str]],
    required_groups: list[str],
    all_tags: list[str],
) -> None:
    """
    对核心分类进行检查。

    默认不把“全部节点”偷偷塞到地区/AI/流媒体/低倍率组，因为这会改变
    selector 的实际意义。若确实需要这种回退，可以以后加 --fallback-all。
    """
    missing: list[str] = []
    for group in required_groups:
        if not groups.get(group):
            missing.append(group)

    if missing:
        print("!! 以下分组没有匹配到订阅节点:", file=sys.stderr)
        for group in missing:
            print(f"   - {group}", file=sys.stderr)
        print("!! 不生成 config.json，避免产生语义错误的节点组。", file=sys.stderr)
        print("!! 请检查 Sub-Store 节点 tag 是否包含对应地区/功能关键词。", file=sys.stderr)
        raise SystemExit(2)


# -----------------------------------------------------------------------------
# 合并
# -----------------------------------------------------------------------------
def merge_config(template_path: Path, nodes: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        config = json.loads(template_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"!! 找不到模板文件: {template_path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"!! 模板 JSON 无效: {template_path}\n{exc}")

    if not isinstance(config, dict):
        raise SystemExit("!! 模板根对象必须是 JSON object")

    all_tags = [node["tag"] for node in nodes]
    all_tag_set = set(all_tags)

    # 避免重复注入相同订阅节点。
    strip_old_subscription_nodes(config, all_tag_set)
    append_nodes(config, nodes)

    groups = classify(all_tags)

    # 核心分组：没有命中就停止，避免把所有节点错误地当作某一区域。
    require_matches(
        groups,
        [
            "香港手动",
            "日本手动",
            "狮城手动",
            "美国手动",
            "AI手动",
            "流媒体手动",
            "低倍率手动",
        ],
        all_tags,
    )

    # -------------------------------------------------------------------------
    # 节点组
    # -------------------------------------------------------------------------
    ensure_selector(config, "香港手动", groups["香港手动"])
    ensure_selector(config, "日本手动", groups["日本手动"])
    ensure_selector(config, "狮城手动", groups["狮城手动"])
    ensure_selector(config, "美国手动", groups["美国手动"])
    ensure_selector(config, "AI手动", groups["AI手动"])

    # “稳定”组采用 urltest，而不是 selector。
    ensure_urltest(
        config,
        "流媒体手动",
        groups["流媒体手动"],
        url="https://www.gstatic.com/generate_204",
        interval="5m",
        tolerance=50,
    )
    ensure_urltest(
        config,
        "低倍率手动",
        groups["低倍率手动"],
        url="https://www.gstatic.com/generate_204",
        interval="5m",
        tolerance=50,
    )

    # 全量节点组。
    ensure_selector(config, "手动选择", all_tags)
    ensure_urltest(
        config,
        "自动选择",
        all_tags,
        url="https://www.gstatic.com/generate_204",
        interval="5m",
        tolerance=50,
    )

    # -------------------------------------------------------------------------
    # 业务 selector：完全按用户给出的结构重写
    # -------------------------------------------------------------------------
    for tag, definition in SELECTOR_DEFINITIONS.items():
        ensure_selector(
            config,
            tag,
            list(definition["outbounds"]),
            definition.get("default"),
        )

    # 确保每一个 selector 引用的 outbound 都确实存在。
    existing_tags = {
        ob.get("tag")
        for ob in config.get("outbounds", [])
        if isinstance(ob, dict) and isinstance(ob.get("tag"), str)
    }

    unresolved: list[tuple[str, str]] = []
    for selector_tag, definition in SELECTOR_DEFINITIONS.items():
        for target in definition["outbounds"]:
            if target not in existing_tags:
                unresolved.append((selector_tag, target))

    if unresolved:
        print("!! 存在未解析的 selector 引用:", file=sys.stderr)
        for selector_tag, target in unresolved:
            print(f"   - {selector_tag} -> {target}", file=sys.stderr)
        raise SystemExit(3)

    return config


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="生成 N60Pro sing-box 1.15 配置文件"
    )
    parser.add_argument("--url", default=DEFAULT_SUB_URL, help="Sub-Store sing-box 订阅地址")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help="模板文件，默认 n60pro-singbox-1.15-alpha9.json",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="输出文件，默认 config.json",
    )
    args = parser.parse_args()

    template_path = Path(args.template)
    output_path = Path(args.output)

    print("==> 1. 拉取 Sub-Store collection/JC sing-box 订阅")
    print(f"    URL: {args.url}")
    raw_nodes = fetch_nodes(args.url)
    print(f"    返回 outbound: {len(raw_nodes)}")

    nodes = clean_nodes(raw_nodes)
    print(f"    有效代理节点: {len(nodes)}")

    if not nodes:
        raise SystemExit("!! 没有获得任何可用代理节点，停止生成。")

    print("==> 2. 按 tag 去重并分类")
    config = merge_config(template_path, nodes)

    print("==> 3. 写入 config.json")
    output_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"    输出: {output_path}")
    print(f"    outbound 总数: {len(config.get('outbounds', []))}")

    for group in [
        "香港手动",
        "日本手动",
        "狮城手动",
        "美国手动",
        "AI手动",
        "流媒体手动",
        "低倍率手动",
        "手动选择",
        "自动选择",
    ]:
        ob = find_outbound(config, group)
        if ob is not None:
            print(f"    {group}: {len(ob.get('outbounds', []))}")

    print("==> 完成")


if __name__ == "__main__":
    main()
