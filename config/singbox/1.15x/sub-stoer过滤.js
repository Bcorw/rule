function operator(proxies) {
  const keywords = ["官方", "推荐", "剩余", "距离", "重置", "改为", "更新订阅", "到期", "流量", "官网"];
  return proxies.filter(p => {
    // 1. 如果节点名字包含上述任意关键词，则剔除
    if (p.name && keywords.some(k => p.name.includes(k))) {
      return false;
    }
    // 2. 很多机场的流量信息节点，地址会填 127.0.0.1、0.0.0.0 或 invalid
    if (p.server && (p.server === "127.0.0.1" || p.server === "0.0.0.0" || p.server.includes("invalid"))) {
      return false;
    }
    return true;
  });
}
