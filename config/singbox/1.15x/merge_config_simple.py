#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精简版：从电脑上的 Sub-Store 拉取 sing-box 节点，写入 singbox.json。"""

import json
import os
import re
import urllib.request
from pathlib import Path

# ===== 只需要改这里 =====
SUB_STORE_URL = os.getenv(
    "SUB_STORE_URL",
    "http://你的电脑IP:端口/mJ2mR3tH2gN3xU4v/download/collection/JC?target=sing-box",
)
TEMPLATE = "./linux_mini.json"
OUTPUT = "./config.json"

GROUPS = [
    "日本手动", "狮城手动", "香港手动", "美国手动",
    "AI手动", "流媒体手动", "低倍率手动", "手动选择", "自动选择",
]

REGION = {
    "日本手动": ["日本", "日区", "japan", "tokyo", "osaka", "东京", "大阪", "名古屋", "福冈", "札幌"],
    "狮城手动": ["新加坡", "singapore", "singapura", "狮城"],
    "香港手动": ["香港", "港区", "hong kong", "hongkong", "香江"],
    "美国手动": ["美国", "美区", "usa", "united states", "america", "los angeles", "洛杉矶", "西雅图", "纽约", "旧金山", "圣何塞", "芝加哥", "达拉斯", "迈阿密"],
}
REGION_CODE = {"日本手动": "jp", "狮城手动": "sg", "香港手动": "hk", "美国手动": "us"}

# 增加香港与澳门的排除关键词和地区代码（用于排除 AI 节点）
EXCLUDE_AI_HK_MO = ["香港", "港区", "hong kong", "hongkong", "香江", "澳门", "澳門", "macau", "macao"]
EXCLUDE_AI_HK_MO_CODES = ["hk", "mo"]

AI = ["通用","ai", "openai", "chatgpt", "gpt", "claude", "anthropic", "gemini", "bard", "copilot", "grok", "perplexity", "poe", "mistral", "deepseek", "qwen", "千问", "通义", "豆包", "智谱", "kimi", "月之暗面"]
MEDIA = ["流媒体", "奈飞", "netflix", "disney", "disney+", "disneyplus", "hbo", "max", "hulu", "primevideo", "prime video", "youtube", "bilibili", "哔哩哩哔", "tiktok", "spotify", "stream", "streaming", "解锁", "原生", "住宅ip"]
LOW_RATE = [
    re.compile(r"(?<![0-9])0(?:\.\d+)?\s*[x倍](?![a-z])", re.I),
    re.compile(r"倍率\s*[:：]?\s*0(?:\.\d+)?", re.I),
    re.compile(r"低倍率", re.I),
    re.compile(r"low[\s_-]*rate", re.I),
]

NON_NODE = {"selector", "urltest", "direct", "block", "dns", "dns-rule", "tun", "mixed"}


def contains(tag, word):
    return word.casefold() in tag.casefold()


def region_match(tag, group):
    if any(contains(tag, x) for x in REGION[group]):
        return True
    code = REGION_CODE[group]
    return re.search(rf"(?<![a-z0-9]){code}(?![a-z0-9])", tag, re.I) is not None


def is_hk_mo(tag):
    """判断节点是否属于香港或澳门"""
    if any(contains(tag, x) for x in EXCLUDE_AI_HK_MO):
        return True
    return any(re.search(rf"(?<![a-z0-9]){code}(?![a-z0-9])", tag, re.I) is not None for code in EXCLUDE_AI_HK_MO_CODES)


def is_node(x):
    tag = str(x.get("tag", "")).strip()
    typ = str(x.get("type", "")).lower().strip()
    return bool(tag and typ and typ not in NON_NODE and any(k in x for k in ("server", "address", "endpoint")))


def main():
    if "你的电脑IP:端口" in SUB_STORE_URL:
        raise SystemExit("请先把 SUB_STORE_URL 里的“你的电脑IP”改成运行 Sub-Store 的电脑局域网 IP。")

    print("正在拉取 Sub-Store：", SUB_STORE_URL)
    with urllib.request.urlopen(SUB_STORE_URL, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))

    if isinstance(data, dict):
        raw = data.get("outbounds", data.get("proxies", []))
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    nodes = []
    seen = set()
    for x in raw:
        if not isinstance(x, dict) or not is_node(x):
            continue
        tag = x["tag"].strip()
        if tag in seen:
            continue
        seen.add(tag)
        nodes.append(x)

    if not nodes:
        raise SystemExit("Sub-Store 没有返回可用代理节点，未写入配置。")

    template = json.loads(Path(TEMPLATE).read_text(encoding="utf-8"))
    outbounds = template.get("outbounds", [])

    # 模板中已有 tag 不重复写入；订阅节点只追加到根 outbounds。
    existing = {str(x.get("tag")) for x in outbounds if isinstance(x, dict) and x.get("tag")}
    new_nodes = [x for x in nodes if x["tag"] not in existing]
    outbounds.extend(new_nodes)

    groups = {g: [] for g in GROUPS}
    all_tags = [x["tag"] for x in new_nodes]

    for x in new_nodes:
        tag = x["tag"]
        for g in ("日本手动", "狮城手动", "香港手动", "美国手动"):
            if region_match(tag, g):
                groups[g].append(tag)

        # 匹配 AI 节点，且排除香港与澳门
        is_ai_node = (
            re.search(r"(?<![a-z0-9])ai(?![a-z0-9])", tag, re.I) is not None
            or any(contains(tag, k) for k in AI if k != "ai")
        )
        if is_ai_node and not is_hk_mo(tag):
            groups["AI手动"].append(tag)

        if any(contains(tag, k) for k in MEDIA):
            groups["流媒体手动"].append(tag)
        if any(p.search(tag) for p in LOW_RATE):
            groups["低倍率手动"].append(tag)

    groups["手动选择"] = all_tags[:]
    groups["自动选择"] = all_tags[:]

    for x in outbounds:
        if x.get("tag") in GROUPS:
            x["outbounds"] = groups[x["tag"]]

    Path(OUTPUT).write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n写入节点：{len(new_nodes)} 个")
    for g in GROUPS:
        print(f"{g:<6} {len(groups[g]):>4} 个")
    print(f"\n输出：{OUTPUT}")


if __name__ == "__main__":
    main()