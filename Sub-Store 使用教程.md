**注意：重启后配置丢失的，命令里的文件映射地址 /mnt/sub-store/data，根据自己设备挂载修改。**

### Docker 部署（bridge 网络，需改防火墙）

```apache
docker run -d \
--name=sub-store \
--restart=always \
-e SUB_STORE_BACKEND_MERGE=true \
-e SUB_STORE_BACKEND_API_PORT=3001 \
-e SUB_STORE_FRONTEND_BACKEND_PATH=/<你的后端路径> \
-e "SUB_STORE_CORS_ALLOWED_ORIGINS=http://192.168.10.11:3001" \
-e "SUB_STORE_BACKEND_SYNC_CRON=55 23 * * *" \
-p 3001:3001 \
-v /etc/sub-store/data:/opt/app/data \
xream/sub-store:latest
```

### Docker 部署（host 网络，不用改防火墙）

```apache
docker run -d \
--name=sub-store \
--restart=always \
--network host \
-e SUB_STORE_BACKEND_MERGE=true \
-e SUB_STORE_BACKEND_API_PORT=3001 \
-e SUB_STORE_FRONTEND_BACKEND_PATH=/<你的后端路径> \
-e "SUB_STORE_CORS_ALLOWED_ORIGINS=http://192.168.10.11:3001" \
-e "SUB_STORE_BACKEND_SYNC_CRON=55 23 * * *" \
-v /etc/sub-store/data:/opt/app/data \
xream/sub-store:latest
```

### Podman 部署（VPS 等 Linux 服务器）

```apache
podman run -d \
--name=sub-store \
--restart=always \
-e SUB_STORE_BACKEND_MERGE=true \
-e SUB_STORE_BACKEND_API_PORT=3001 \
-e SUB_STORE_FRONTEND_BACKEND_PATH=/<你的后端路径> \
-e "SUB_STORE_CORS_ALLOWED_ORIGINS=http://<服务器IP>:3001" \
-e "SUB_STORE_BACKEND_SYNC_CRON=55 23 * * *" \
-p 3001:3001 \
-v /etc/sub-store/data:/opt/app/data \
docker.io/xream/sub-store:latest
```

### Docker 查看启动日志

```apache
换行折叠复制
apachedocker logs -f -t --tail 100 sub-store
```

### OpenWrt Docker 部署报错 `failed to mount ... overlay ... invalid argument`

原因：Docker 29 起默认 containerd 镜像存储，数据目录 `/opt/docker` 在 overlay 根目录上无法建容器。

确认问题：类型显示为 `overlay` 即是此问题。

```bash
换行折叠复制
bashdf -hT /opt/docker
```

修改数据目录：

```swift
/etc/init.d/dockerd stop
uci set dockerd.globals.data_root='/overlay/docker/'
uci commit dockerd
/etc/init.d/dockerd start
```

验证：显示 `/overlay/docker` 后重新部署。

```nginx
换行折叠复制
nginxdocker info --format '{{.Driver}} | {{.DockerRootDir}}'
```

### Docker 手动更新

```bash
docker pull xream/sub-store:latest
docker rm -f sub-store
```

然后再执行一遍上面的部署命令。

### Docker 自动更新（Watchtower）

Docker 29 需加 `DOCKER_API_VERSION`。

```apache
docker run -d \
--name watchtower \
--restart=always \
-e DOCKER_API_VERSION=1.40 \
-v /var/run/docker.sock:/var/run/docker.sock \
containrrr/watchtower \
--interval 3600 sub-store
```

### Cachyos Docker Compose

```bash
mkdir -p /home/leo/docker/Sub-Store/data
mkdir -p /home/leo/docker/Sub-Store/docker-compose.yml

services:
  sub-store:
    image: xream/sub-store:latest
    container_name: sub-store
    restart: always
    ports:
      - "3001:3001"
    environment:
      SUB_STORE_BACKEND_MERGE: "true"
      SUB_STORE_BACKEND_API_PORT: "3001"
      SUB_STORE_FRONTEND_BACKEND_PATH: "/你的后端路径"
      SUB_STORE_CORS_ALLOWED_ORIGINS: "http://服务器IP:3001"
      SUB_STORE_BACKEND_SYNC_CRON: "55 23 * * *"
    volumes:
      - ./data:/opt/app/data
      
cd /home/leo/docker/Sub-Store
docker compose up -d
```

### 配置与脚本

**机场订阅链接后缀**

加在：单条订阅的机场链接末尾。每条订阅的 `cacheKey` 不同。

```bash
机场订阅链接#cacheKey=a&noFlow
```

**过滤流量 / 到期信息节点的正则**

填在：订阅 → 节点操作 → 正则过滤，模式选过滤模式。

```undefined
剩余|距离|套餐|到期|官网
```



**mihomo模板：**

```bash
https://raw.githubusercontent.com/Bcorw/rule/refs/heads/main/config/mihomo/config/overwrite.yaml
```





**singbox模板：**

```bash
https://raw.githubusercontent.com/Bcorw/rule/refs/heads/main/config/singbox/1.15x/Linux.json
```

**sing-box 模板配套脚本**

脚本A——组合订阅&name=Flow-Serve

```bash
https://gh-proxy.com/https://raw.githubusercontent.com/xream/scripts/main/surge/modules/sub-store-scripts/sing-box/template.js#type=组合订阅&name=Flow-Serve&outbound=🕳ℹ️自动选择🕳ℹ️香港自动|香港手动🏷ℹ️🇭🇰|HK|hk|香港|港|Hong Kong🕳ℹ️日本自动|日本手动🏷ℹ️🇯🇵|JP|jp|日本|日|Japan🕳ℹ️狮城自动|狮城手动🏷ℹ️🇸🇬|SG|sg|新加坡|坡|狮城|Singapore🕳ℹ️美国自动|美国手动🏷ℹ️🇺🇸|US|us|美国|美|United States
```

脚本B——组合订阅&name=AI-Serve

```bash
https://gh-proxy.com/https://raw.githubusercontent.com/xream/scripts/main/surge/modules/sub-store-scripts/sing-box/template.js#type=组合订阅&name=AI-Serve&outbound=🕳ℹ️AI自动|AI手动
```

**GitHub 加速代理地址**

```bash
https://gh-proxy.com
```



**mihomo 用 Gist 链接拉节点**
写在：mihomo 客户端配置的 proxy-providers 里。

```yaml
proxy-providers:
substore:
type: http
url: "<Gist 链接>"
interval: 3600
age-secret-key: "AGE-SECRET-KEY-1<你的私钥>"
```

### WebDAV 同步脚本（订阅用）

填在：订阅 → 节点操作 → 脚本操作，类型选远程链接，填入后展开参数修改。

```bash
https://raw.githubusercontent.com/xream/scripts/main/surge/modules/sub-store-scripts/upload/webdav-sub.js#base-url=https%3A%2F%2Fdav.jianguoyun.com%2Fdav&folder=sub-store&file=sub-store.yaml&username=<WebDAV用户名>&password=<WebDAV密码>&target=mihomo&age-public-key=<age公钥>
```

### WebDAV 同步脚本（文件用）

填在：文件 → 脚本操作，类型选远程链接，填入后展开参数修改。

```bash
https://raw.githubusercontent.com/xream/scripts/main/surge/modules/sub-store-scripts/upload/webdav-file.js#base-url=https%3A%2F%2Fdav.jianguoyun.com%2Fdav&folder=sub-store&file=sub-store.txt&username=<WebDAV用户名>&password=<WebDAV密码>&age-public-key=<age公钥>
```