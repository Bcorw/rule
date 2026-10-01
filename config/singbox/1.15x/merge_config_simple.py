#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""针对 linux_mini 模板：支持双订阅源分别拉取常规节点与AI节点。"""

import json
import urllib.request
import re
from pathlib import Path

# ===== 订阅链接配置 =====
# 常规节点订阅
URL_LXY = ""
# AI专用节点订阅 (已经在 Sub-Store 中排除了港澳)
URL_AI = ""

TEMPLATE = "./linux_mini.json"  # 确保文件名与你的模板对应
OUTPUT = "./config.json"

# 需要填入节点的目标组，新增了 AI自动 与 AI手动
GROUPS = [
    "自动选择",
    "香港自动", "香港手动",
    "台湾自动", "台湾手动",
    "日本自动", "日本手动",
    "狮城自动", "狮城手动",
    "美国自动", "美国手动",
    "AI自动", "AI手动"
]

REGION = {
    "香港": ["香港", "港区", "hong kong", "hongkong", "香江"],
    "台湾": ["台湾", "台区", "taiwan", "taipei", "台北", "新北"],
    "日本": ["日本", "日区", "japan", "tokyo", "osaka", "东京", "大阪", "名古屋", "福冈", "札幌"],
    "狮城": ["新加坡", "singapore", "singapura", "狮城"],
    "美国": ["美国", "美区", "usa", "united states", "america", "los angeles", "洛杉矶", "西雅图", "纽约", "旧金山", "圣何塞", "芝加哥", "达拉斯", "迈阿密"],
}
REGION_CODE = {"香港": "hk", "台湾": "tw", "日本": "jp", "狮城": "sg", "美国": "us"}

NON_NODE = {"selector", "urltest", "direct", "block", "dns", "dns-rule", "tun", "mixed"}


def contains(tag, word):
    return word.casefold() in tag.casefold()


def region_match(tag, region_name):
    if any(contains(tag, x) for x in REGION[region_name]):
        return True
    code = REGION_CODE[region_name]
    return re.search(rf"(?<![a-z0-9]){code}(?![a-z0-9])", tag, re.I) is not None


def is_node(x):
    tag = str(x.get("tag", "")).strip()
    typ = str(x.get("type", "")).lower().strip()
    return bool(tag and typ and typ not in NON_NODE and any(k in x for k in ("server", "address", "endpoint")))


def fetch_nodes(url, source_name):
    """封装拉取节点的函数"""
    print(f"正在拉取 {source_name} 订阅...")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"拉取失败 {source_name}: {e}")
        return []

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
    return nodes


def main():
    # 1. 分别从两个链接拉取节点
    lxy_nodes = fetch_nodes(URL_LXY, "LXY 常规")
    ai_nodes = fetch_nodes(URL_AI, "AI-Serve")

    if not lxy_nodes and not ai_nodes:
        raise SystemExit("两个订阅均没有返回可用代理节点，未写入配置。")

    template = json.loads(Path(TEMPLATE).read_text(encoding="utf-8"))
    outbounds = template.get("outbounds", [])

    # 初始化各分组列表
    groups = {g: [] for g in GROUPS}

    # 用于防重复写入全局节点池
    existing_tags = {str(x.get("tag")) for x in outbounds if isinstance(x, dict) and x.get("tag")}
    all_new_nodes = []

    # 2. 处理 LXY 常规节点
    for x in lxy_nodes:
        tag = x["tag"]
        # 加进全局池
        if tag not in existing_tags:
            all_new_nodes.append(x)
            existing_tags.add(tag)

        # 归类到地区组
        groups["自动选择"].append(tag)
        for region_name in REGION.keys():
            if region_match(tag, region_name):
                groups[f"{region_name}自动"].append(tag)
                groups[f"{region_name}手动"].append(tag)

    # 3. 处理 AI-Serve 专属节点
    for x in ai_nodes:
        tag = x["tag"]
        # 加进全局池 (如果节点名跟常规节点重复，则不再重复添加 outbound 本身，但仍参与分组)
        if tag not in existing_tags:
            all_new_nodes.append(x)
            existing_tags.add(tag)

        # 仅仅写入 AI专属 分组
        groups["AI自动"].append(tag)
        groups["AI手动"].append(tag)

    # 4. 组装数据并输出
    outbounds.extend(all_new_nodes)

    for x in outbounds:
        if x.get("tag") in GROUPS:
            x["outbounds"] = groups[x["tag"]]

    Path(OUTPUT).write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n配置合并完成！共拉取 {len(lxy_nodes)} 个常规节点，{len(ai_nodes)} 个 AI 节点。")
    print("-" * 30)
    for g in GROUPS:
        print(f"{g:<8} {len(groups[g]):>4} 个")
    print("-" * 30)
    print(f"输出文件：{OUTPUT}")


if __name__ == "__main__":
    main()
