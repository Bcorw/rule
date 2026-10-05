// 过滤掉香港、澳门节点
async function operator(proxies, targetPlatform, context) {
  const excludePattern = /🇭🇰|🇲🇴|香港|澳门|流量|教育|双鱼座|Hong\s*Kong|Macau|Macao/i;

  return proxies.filter(proxy => {
    const name = proxy.name || '';
    return !excludePattern.test(name);
  });
}
