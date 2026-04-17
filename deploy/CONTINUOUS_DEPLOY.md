# InsightTrader 持续部署手册

目标服务器：`93901.pro`

## 部署版本号规范

- 版本文件：`deploy/VERSION`
- 每次部署前，都必须先更新 `deploy/VERSION` 内的版本号
- 版本号格式固定为：`yyyy.mmdd.hhmm`
- 示例：`2026.0416.1534`

建议在开始执行下面任一部署场景前，先运行：

```powershell
Set-Content -Path .\deploy\VERSION -Value (Get-Date -Format 'yyyy.MMdd.HHmm')
Get-Content .\deploy\VERSION
```

## 前置：设置本机变量

> 每次打开新 PowerShell 终端后执行一次，后续命令直接复制粘贴。

```powershell
# 项目根目录（根据本机实际路径修改）
$REPO = ".\"

# SSH 私钥路径（根据本机实际路径修改）
$PEM  = "$env:USERPROFILE\.ssh\InsightTrader.pem"
```

---

## 快速决策表

| 改动范围 | 执行场景 | 预计耗时 |
|---------|---------|---------|
| 只改 Python 逻辑（无依赖变化） | [场景 A](#场景-a仅更新后端) | ~1~3 min |
| 新增/升级 Python 依赖（`pyproject.toml` 或 `uv.lock` 有变更） | [场景 A](#场景-a仅更新后端) | ~5~10 min |
| 只改前端 | [场景 B](#场景-b仅更新前端) | ~2 min |
| 前后端都改 | [场景 C](#场景-c前后端同时更新) | ~3~12 min |
| 只改环境变量 | [场景 D](#场景-d更新环境变量) | <1 min |
| 只改 Nginx 配置 | [场景 E](#场景-e更新-nginx-配置) | <1 min |

---

## 场景 A：仅更新后端

适用于 `ta_service/`、`tradingagents/`、`Dockerfile.ta_service`、`docker-compose.prod.yml`、`pyproject.toml`、`uv.lock` 有变更。

```powershell
# 0. 更新部署版本号
Set-Content -Path .\deploy\VERSION -Value (Get-Date -Format 'yyyy.MMdd.HHmm')

# 1. 上传后端代码
cd $REPO
python deploy/upload.py

# 2. 重新构建并重启（仅 ta_service，不影响 mongo/redis 数据）
ssh -i $PEM root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml build ta_service && docker compose -f docker-compose.prod.yml up -d ta_service"

# 3. 验证
ssh -i $PEM root@93901.pro "curl -s http://127.0.0.1:8100/health"
```

期望输出：返回 `status=ok`，并带上 `version`、`mongo`、`redis`、`writable_dirs` 检查结果。

> **说明**
> - 后端镜像现在分两层安装：先基于 `pyproject.toml + uv.lock` 执行 `uv sync --frozen --no-dev --no-editable --no-install-project` 安装锁定依赖，再在复制源码后执行 `uv sync --frozen --no-dev --no-editable` 安装当前项目。
> - `python deploy/upload.py` 会把远端构建需要的新版本 `uv.lock` 和 `README.md` 一并上传；否则远端可能继续使用旧锁文件，或在 `COPY pyproject.toml uv.lock README.md ./` 时直接失败。
> - 只改 Python 逻辑（无依赖变化）时，依赖层通常会命中缓存，不应再每次重新下载整套依赖；`build` 通常约 **1~3 分钟**。
> - 只有 `pyproject.toml` 或 `uv.lock` 变化时，依赖层才会重新安装，约 **5~10 分钟**。
> - 如果修改了依赖，提交前必须同步更新 `uv.lock`，否则生产构建会因 `--frozen` 失败。
> - `mongo` 和 `redis` 容器不受影响，数据通过 Docker volume 持久化。

---

## 场景 B：仅更新前端

适用于 `mobile_h5/` 有变更。

```powershell
# 0. 更新部署版本号
Set-Content -Path .\deploy\VERSION -Value (Get-Date -Format 'yyyy.MMdd.HHmm')

# 1. 本地构建（服务器不需要 Node.js）
cd $REPO\mobile_h5
npm run build

# 2. 上传 dist/ 到服务器
cd $REPO
python deploy/upload_dist.py
```

> Nginx 直接读取静态文件目录，无需重启任何服务，上传完成后刷新浏览器即生效。

---

## 场景 C：前后端同时更新

按顺序执行场景 A 和场景 B：

```powershell
# ── 更新部署版本号 ──────────────────────────────────────────────────────────────
Set-Content -Path .\deploy\VERSION -Value (Get-Date -Format 'yyyy.MMdd.HHmm')

# ── 后端 ──────────────────────────────────────────────────────────────────────
cd $REPO
python deploy/upload.py
ssh -i $PEM root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml build ta_service && docker compose -f docker-compose.prod.yml up -d ta_service"

# ── 前端 ──────────────────────────────────────────────────────────────────────
cd $REPO\mobile_h5
npm run build
cd $REPO
python deploy/upload_dist.py

# ── 验收 ──────────────────────────────────────────────────────────────────────
ssh -i $PEM root@93901.pro "curl -s http://127.0.0.1:8100/health && curl -sk -o /dev/null -w 'Nginx HTTPS %{http_code}' https://127.0.0.1/"
```

期望输出：`health.status=ok` + `Nginx HTTPS 200`

---

## 场景 D：更新环境变量

适用于修改了 `deploy/write_env.sh`（如更换 API Key、调整超时时长等）。

```powershell
# 0. 更新部署版本号
Set-Content -Path .\deploy\VERSION -Value (Get-Date -Format 'yyyy.MMdd.HHmm')

# 1. 上传脚本并在服务器执行，覆盖写入 /opt/insighttrader/.env
scp -i $PEM deploy\write_env.sh root@93901.pro:/root/write_env.sh
ssh -i $PEM root@93901.pro "bash /root/write_env.sh"

# 2. 重启 ta_service 使新配置生效
ssh -i $PEM root@93901.pro "cd /opt/insighttrader && docker compose -f docker-compose.prod.yml up -d ta_service"

# 3. 验证关键变量已写入
ssh -i $PEM root@93901.pro "grep TA_SERVICE_ENV /opt/insighttrader/.env"
```

期望输出：`TA_SERVICE_ENV=production`

---

## 场景 E：更新 Nginx 配置

适用于修改了 `deploy/nginx.conf`（如调整超时、缓存策略等）。

```powershell
# 0. 更新部署版本号
Set-Content -Path .\deploy\VERSION -Value (Get-Date -Format 'yyyy.MMdd.HHmm')

# 上传新配置，验证语法后无停机热重载
scp -i $PEM deploy\nginx.conf root@93901.pro:/opt/insighttrader/deploy/nginx.conf
ssh -i $PEM root@93901.pro "cp /opt/insighttrader/deploy/nginx.conf /etc/nginx/sites-available/insighttrader && nginx -t && systemctl reload nginx"
```

---

## 常见问题

### 容器启动后 /health 无响应

```bash
# 在服务器上查看启动日志
cd /opt/insighttrader
docker compose -f docker-compose.prod.yml logs --tail=50 ta_service
```

### 分析任务日志

```bash
docker exec insighttrader-ta_service-1 tail -f /home/appuser/app/logs/ta_service.log
```

### 强制全量重建（依赖异常时使用）

```bash
cd /opt/insighttrader
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build --no-cache ta_service
docker compose -f docker-compose.prod.yml up -d
```
