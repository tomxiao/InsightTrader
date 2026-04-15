# InsightTrader v1.1 部署前准备清单

## 1. 适用范围

本文档适用于移动端 H5 会话页 v1.1 版本上线前的部署准备。

本次版本包含：

- 前端改动
- 后端改动
- 测试与验收补充

因此本次部署默认按 [CONTINUOUS_DEPLOY.md](./CONTINUOUS_DEPLOY.md) 中的“场景 C：前后端同时更新”执行。

## 2. 本次部署结论

### 2.1 部署策略

本次不应直接跳过检查进入部署。

建议先完成发布前清理与校验，再执行持续部署。

### 2.2 推荐顺序

1. 锁定发布范围
2. 执行本地发布前校验
3. 确认 SSH 与部署变量
4. 按场景 C 执行部署
5. 完成部署后技术验收与业务验收

## 3. 部署前必须完成的准备

### 3.1 锁定发布范围

部署前必须先确认哪些文件属于本次 v1.1 正式发布内容，哪些不属于。

当前工作区可能包含以下几类内容：

- v1.1 功能代码
- 测试代码
- 文档
- 个人环境文件
- 与本次上线无关的已有改动

处理原则：

- 仅发布本次 v1.1 所需的前后端代码
- 文档通常不影响线上运行，可不作为上线阻断项
- 个人环境文件不得进入发布范围
- 未确认用途的历史改动不得默认跟随上线

当前特别需要注意：

- `.codex/environments/environment.toml` 不应进入发布范围
- `mobile_h5/src/api/conversations.ts` 如不是本次需求必要改动，不应默认随版本部署

### 3.2 本地发布前校验

以下校验项必须全部通过：

#### 前端构建

```powershell
cd D:\CodeBase\InsightTrader\mobile_h5
npm run build
```

#### 前端自动化验收

```powershell
cd D:\CodeBase\InsightTrader\mobile_h5
npm run test -- src/views/conversation/__tests__/ConversationPage.test.ts
```

#### 前端类型检查

```powershell
cd D:\CodeBase\InsightTrader\mobile_h5
npm run type-check
```

#### 后端状态映射与契约测试

```powershell
cd D:\CodeBase\InsightTrader
pytest tests/test_ta_service_status_mapper.py tests/test_ta_service_conversations_contracts.py
```

### 3.3 SSH 与部署变量确认

每次打开新 PowerShell 终端后，先执行：

```powershell
$REPO = ".\"
$PEM  = "$env:USERPROFILE\.ssh\InsightTrader.pem"
```

部署前确认以下内容：

- `$REPO` 指向当前项目根目录
- `$PEM` 指向正确的 SSH 私钥文件
- 私钥文件存在且可用

## 4. 本次是否需要环境变量或 Nginx 变更

根据当前版本内容判断：

- 不属于仅环境变量变更
- 不属于仅 Nginx 配置变更
- 当前没有明确证据表明需要执行场景 D 或场景 E

因此本次部署默认不改 `.env`，也不改 Nginx。

若部署前发现以下文件有实际变更，则需重新评估：

- `deploy/write_env.sh`
- `deploy/nginx.conf`

## 5. 部署执行方式

本次默认执行场景 C。

参考命令：

```powershell
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

## 6. 部署后验收

### 6.1 技术验收

部署完成后，至少确认：

- `ta_service /health` 返回 `{"status":"ok"}`
- Nginx HTTPS 返回 `200`

### 6.2 业务验收

本次版本不能只看健康检查，还应补充业务验证：

1. 打开移动端当前会话页
2. 检查 `task_status` 是否仍为单卡片结构
3. 检查时间线节点与当前阶段 spinner 是否正常
4. 发起一次真实分析任务
5. 检查分析完成后是否进入完成态
6. 检查 `小I` 是否仍为统一系统角色
7. 检查前端轮询模式下状态是否正常推进

## 7. 本次部署门槛

满足以下条件后，才建议部署：

- 发布范围已确认
- 无无关文件混入发布
- 前端构建通过
- 前端自动化验收通过
- 前端类型检查通过
- 后端状态映射与契约测试通过
- SSH 私钥和部署变量确认无误

## 8. 最终建议

本次正确做法不是直接部署，而是：

1. 先清理并确认发布范围
2. 跑完全部发布前校验
3. 全部通过后，再按场景 C 部署

建议对外执行口径：

`通过发布前校验后，按前后端同时更新方案部署。`
