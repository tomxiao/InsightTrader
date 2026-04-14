# InsightTrader 初始部署手册

目标服务器：Ubuntu 24.04 LTS（阿里云 ECS）  
域名：`93901.pro`（前端 + 后端 API，通过路径 `/api/` 区分）  
SSH 登录：`ssh -i C:\Users\tomxiao\.ssh\InsightTrader.pem root@93901.pro`

---

## 架构

```
用户浏览器
    │ HTTP :80
  Nginx（宿主机）
    ├── 93901.pro/      → /opt/insighttrader/mobile_h5/dist/（静态文件）
    └── 93901.pro/api/  → 127.0.0.1:8100（反向代理，去掉 /api 前缀）
                               │
                          ta_service 容器（FastAPI + Worker）
                            ├── mongo 容器
                            └── redis 容器
```

---

## 第一步：服务器初始化

> 每台新服务器只需执行一次。已初始化的服务器跳过此步。

### 1-1 安装 Docker

```bash
# 登录服务器
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro

# 卸载可能冲突的旧包
apt remove -y docker.io docker-compose docker-compose-v2 containerd runc 2>/dev/null || true

# 安装依赖
apt update && apt install -y ca-certificates curl gnupg lsb-release

# 添加 Docker GPG Key 和源（使用阿里云镜像）
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

# 安装 Docker CE
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 配置 DaoCloud 镜像加速（国内无法访问 DockerHub）
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
EOF

# 启动（若失败先 reset）
systemctl reset-failed docker.socket docker.service 2>/dev/null || true
systemctl enable docker
systemctl start docker.socket
systemctl start docker.service

# 验证
docker version && docker compose version
```

### 1-2 安装 Nginx

```bash
apt install -y nginx
systemctl enable nginx
systemctl start nginx
```

### 1-3 配置防火墙

```bash
ufw allow 22
ufw allow 80
ufw --force enable
ufw status
```

### 1-4 安装 Node.js（用于本地构建，服务器上不需要）

> 服务器不需要 Node.js，前端在本地构建后上传 `dist/`。

---

## 第二步：上传代码到服务器

> 本步骤在本地 PowerShell 执行。`upload.py` 使用 paramiko 传输，无需 rsync。

### 前提条件

```powershell
# 确认 paramiko 已安装
python -m pip install paramiko
```

### 执行上传

```powershell
# 在项目根目录执行
cd D:\CodeBase\InsightTrader
python deploy/upload.py
```

`upload.py` 白名单只上传必要内容：`ta_service/`、`tradingagents/`、`tests/`、`deploy/`，以及 `Dockerfile.ta_service`、`docker-compose.prod.yml`、`pyproject.toml`、`.env.production.example`。

脚本会自动创建远端 `/opt/insighttrader/` 目录，无需手动创建。

---

## 第三步：配置生产环境变量

`deploy/write_env.sh` 含有真实 Key，已加入 `.gitignore`，不会提交 git。

```powershell
# 上传脚本到服务器
scp -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" deploy\write_env.sh root@93901.pro:/root/write_env.sh

# 在服务器执行，写入 .env
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "bash /root/write_env.sh"

# 验证写入成功
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "grep TA_SERVICE_ENV /opt/insighttrader/.env"
```

期望输出：`TA_SERVICE_ENV=production`

`write_env.sh` 写入的关键变量：

| 变量 | 值 |
|------|----|
| `TA_SERVICE_ENV` | `production` |
| `TA_SERVICE_HOST` | `0.0.0.0` |
| `TA_SERVICE_PORT` | `8100` |
| `TA_SERVICE_MONGO_URI` | `mongodb://mongo:27017` |
| `TA_SERVICE_REDIS_URL` | `redis://redis:6379/0` |
| `TA_SERVICE_CORS_ORIGINS` | `http://93901.pro,http://www.93901.pro` |
| `TA_SERVICE_REPORTS_DIR` | `./reports` |

---

## 第四步：构建并启动后端容器

> 国内阿里云服务器无法访问 DockerHub，`Dockerfile.ta_service` 和 `docker-compose.prod.yml` 中已使用 `m.daocloud.io/docker.io/library/` 前缀的镜像名，pip 依赖走清华镜像。  
> 首次构建需下载基础镜像和所有 pip 依赖，约需 **10～15 分钟**。

```powershell
# 构建镜像（耗时较长，请耐心等待）
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml build"

# 启动所有容器
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml up -d"

# 等待 healthcheck 通过（start_period 为 20s，等待 30s）
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "sleep 30 && cd /opt/insighttrader && docker compose -f docker-compose.prod.yml ps && curl -s http://127.0.0.1:8100/health"
```

期望输出：三个容器均为 `Up (healthy)`，`curl` 返回 `{"status":"ok"}`。

---

## 第五步：构建前端并上传

> 在本地执行，服务器不需要 Node.js 环境。

```powershell
# 进入前端目录，安装依赖（首次或 package.json 有变更时执行）
cd D:\CodeBase\InsightTrader\mobile_h5
npm install

# 构建生产包（产物在 mobile_h5/dist/）
npm run build

# 上传 dist/ 到服务器
cd D:\CodeBase\InsightTrader
python deploy/upload_dist.py
```

---

## 第六步：配置 Nginx

```powershell
# 部署 Nginx 配置、启用站点、重载
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cp /opt/insighttrader/deploy/nginx.conf /etc/nginx/sites-available/insighttrader && ln -sf /etc/nginx/sites-available/insighttrader /etc/nginx/sites-enabled/insighttrader && rm -f /etc/nginx/sites-enabled/default && nginx -t && systemctl reload nginx"

# 验证前端可访问
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "curl -s -o /dev/null -w 'Nginx HTTP %{http_code}' http://127.0.0.1/"
```

期望输出：`Nginx HTTP 200`

---

## 第七步：创建用户

```powershell
# 管理员
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username admin --password 800808aa --role admin"

# 普通用户（逐个执行，避免 PowerShell 变量转义问题）
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username fengj --password 11223344 --role user"
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username lijx --password 11223344 --role user"
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username lvz --password 11223344 --role user"
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username lubx --password 11223344 --role user"
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username ziza --password 11223344 --role user"
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml exec ta_service python ta_service/scripts/create_user.py --username kb --password 11223344 --role user"
```

---

## 第八步：配置开机自启

```powershell
# 上传 systemd service 文件
scp -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" deploy\insighttrader.service root@93901.pro:/etc/systemd/system/insighttrader.service

# 启用开机自启（不立即启动，容器已在运行）
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "systemctl daemon-reload && systemctl enable insighttrader"
```

---

## 验收检查

```powershell
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml ps && curl -s http://127.0.0.1:8100/health && curl -s -o /dev/null -w 'Nginx HTTP %{http_code}' http://127.0.0.1/"
```

期望：三容器 `Up (healthy)`，`{"status":"ok"}`，`Nginx HTTP 200`。

---

## 后续更新部署

```powershell
# 1. 上传最新后端代码
cd D:\CodeBase\InsightTrader
python deploy/upload.py

# 2. 重建并重启后端容器（后端代码有变更时）
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml build ta_service && docker compose -f docker-compose.prod.yml up -d ta_service"

# 3. 更新前端（前端代码有变更时）
cd D:\CodeBase\InsightTrader\mobile_h5
npm run build
cd D:\CodeBase\InsightTrader
python deploy/upload_dist.py
```

---

## 常用运维命令（在服务器上执行）

```bash
# 查看主进程日志（FastAPI 请求日志）
cd /opt/insighttrader
docker compose -f docker-compose.prod.yml logs -f ta_service

# 查看 worker 分析任务日志（更详细，含 LLM 调用和错误堆栈）
docker exec insighttrader-ta_service-1 tail -f /home/appuser/app/logs/ta_service.log

# 重启后端
docker compose -f docker-compose.prod.yml restart ta_service

# 进入容器调试
docker compose -f docker-compose.prod.yml exec ta_service bash

# 查看容器状态
docker compose -f docker-compose.prod.yml ps

# 查看所有容器资源占用
docker stats
```

---

## 附：启用 HTTPS（手动证书）

证书文件存放在 `deploy/cert/`，已加入 `.gitignore`，不提交 git。

### 1. 上传证书到服务器

```powershell
# 创建 ssl 目录
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "mkdir -p /etc/nginx/ssl"

# 上传证书和私钥
scp -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" deploy\cert\93901.pro.pem root@93901.pro:/etc/nginx/ssl/93901.pro.pem
scp -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" deploy\cert\93901.pro.key root@93901.pro:/etc/nginx/ssl/93901.pro.key

# 设置私钥权限
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "chmod 600 /etc/nginx/ssl/93901.pro.key && chmod 644 /etc/nginx/ssl/93901.pro.pem"
```

### 2. 部署 HTTPS Nginx 配置

`deploy/nginx.conf` 已是 HTTPS 版（443 + HTTP 301 重定向），直接覆盖部署：

```powershell
scp -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" deploy\nginx.conf root@93901.pro:/opt/insighttrader/deploy/nginx.conf
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cp /opt/insighttrader/deploy/nginx.conf /etc/nginx/sites-available/insighttrader && ufw allow 443 && nginx -t && systemctl reload nginx"
```

### 3. 更新 CORS 和前端 API 地址

```powershell
# 更新服务器 .env（CORS 改为 https）
scp -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" deploy\write_env.sh root@93901.pro:/root/write_env.sh
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "bash /root/write_env.sh"

# 重启 ta_service 使新 CORS 生效
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml up -d ta_service"
```

### 4. 重建前端并上传

`mobile_h5/.env.production` 中 `VITE_API_BASE_URL` 已是 `https://93901.pro/api`：

```powershell
cd D:\CodeBase\InsightTrader\mobile_h5
npm run build
cd D:\CodeBase\InsightTrader
python deploy/upload_dist.py
```

### 5. 验收

```powershell
ssh -i "C:\Users\tomxiao\.ssh\InsightTrader.pem" root@93901.pro "curl -sk -o /dev/null -w 'HTTPS %{http_code}' https://127.0.0.1/ && curl -s -o /dev/null -w 'HTTP->HTTPS redirect %{http_code}' http://93901.pro/"
```

期望：`HTTPS 200`，`HTTP->HTTPS redirect 301`。

### 证书续期

证书到期后，将新证书文件替换 `deploy/cert/` 中的文件，重新执行第 1、2 步即可。
