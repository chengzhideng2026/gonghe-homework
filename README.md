# Plantcore ERPNext Agent

本项目保留原始说明于 `ORIGINAL_README.md`，ERPNext seed stack 位于 `erpnext/`。桌面 ZIP 中的 `README.md`、`DATASET.md`、`compose.yml` 和 `erpnext/.env.example` 已逐项核对，未覆盖原始文件。Agent 是 Python CLI，通过 ERPNext REST/RPC API 读取实时数据，并通过 OpenAI-compatible chat completions 选择工具。运行时只使用 Python 标准库。

## 启动真实环境

当前开发机尚未安装 Docker Desktop/Engine。Windows 10 Home 用户需要先用管理员 PowerShell 执行 `wsl --install`，按提示重启；如果安装提示固件虚拟化未开启，在 BIOS 开启 Intel VT-x/AMD-V。然后安装 Docker Desktop，选择 WSL 2 based engine，启动 Docker Desktop。重新打开终端确认：

```powershell
docker version              # 必须同时出现 Client 和 Server
docker compose version
```

在项目中启动 ERPNext：

```powershell
cd C:\Users\HP\Documents\ChatGPT\工核homework\erpnext
docker compose up -d
docker compose logs -f restore-site   # 等待 Restore complete.
```

另开终端验证 API：

```powershell
curl.exe -fs -H "Authorization: token crestwind-agent:crestwind-agent-secret" "http://localhost:8080/api/method/frappe.client.get_count?doctype=Item"
# 预期返回 18
```

## 启动 Agent

回到项目根目录，复制 `.env.example` 为 `.env`，填写本地模型配置：

```powershell
Copy-Item .env.example .env
# 编辑 .env：LLM_API_KEY、LLM_MODEL；按服务商需要修改 LLM_BASE_URL
python agent.py
```

不要把真实密钥写入 Git 或发送到对话中。输入问题进行多轮查询；采购订单只能先由模型调用 `prepare_purchase_order` 生成预览，再由用户输入 `/confirm <proposal-id>` 执行，`/quit` 退出。

## 设计

`agent.py` 的 `ERPNextClient` 提供通用元数据、计数、列表查询、详情读取和创建；`LLMRunner` 通过工具 schema 驱动模型；`Agent` 保留 proposal 状态机。所有相对日期以 `REFERENCE_DATE=2025-10-15` 计算，逾期按 `due_date < reference_date` 且 `outstanding_amount > 0` 判断。采购订单创建前校验 item、supplier、qty、uom、rate 和日期，展示预计总额；只有 `/confirm` 才写入，创建后回读。创建失败或超时会锁定 proposal，避免盲目重试。

## 验证状态

本地标准库 `compileall`、7 个单元测试和 `--demo` 已通过。真实 ERPNext API、真实 LLM E2E、README 样例查询和真实采购订单写入必须在 Docker 与模型配置可用后执行；未执行项目不会标记为通过。
