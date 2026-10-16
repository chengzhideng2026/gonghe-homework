# Plantcore ERPNext Agent

本项目保留原始说明于 `ORIGINAL_README.md`，ERPNext seed stack 位于 `erpnext/`。Agent 是 Python CLI，通过 ERPNext REST/RPC API 读取实时数据，并通过 OpenAI-compatible chat completions 选择工具；没有 LLM key 时可用 `--demo` 验证工具层。

## 启动

1. 安装 Docker Desktop 后：`cd erpnext; docker compose up -d`，首次启动等待 `docker compose logs -f restore-site` 出现 Restore complete。
2. 回到项目根目录：`python -m venv .venv; .venv\Scripts\pip install -r requirements.txt`。
3. `Copy-Item .env.example .env`，填入 LLM_API_KEY / LLM_MODEL / LLM_BASE_URL。
4. `python agent.py`，输入问题；输入 `/confirm <proposal-id>` 执行已确认采购订单，`/quit` 退出。

## 设计

`agent.py` 的 `ERPNextClient` 提供通用元数据、列表查询、详情读取和创建；`Agent` 用工具 schema 驱动 LLM，并保留 proposal 状态机。所有相对日期以 `REFERENCE_DATE=2025-10-15` 计算，逾期按 due_date < reference_date 且 outstanding > 0 判断。采购订单创建前校验 item、supplier、qty、uom、rate、日期并展示总额；创建后回读。

## 验证

`python -m unittest discover -s tests` 为本地单元测试。真实 ERPNext API、真实 LLM E2E 和写入测试需在 Docker/密钥可用环境执行，结果写入 HANDOFF.md。
