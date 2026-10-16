# Plantcore ERPNext Agent

本项目保留原始说明于 `ORIGINAL_README.md`，ERPNext seed stack 位于 `erpnext/`。Agent 是 Python CLI，通过 ERPNext REST/RPC API 读取实时数据，并通过 OpenAI-compatible chat completions 选择工具。运行时只使用 Python 标准库；没有 LLM key 时可用 `--demo` 验证本地状态机。

## 启动

1. 安装 Docker Desktop 后：`cd erpnext; docker compose up -d`，首次启动等待 `docker compose logs -f restore-site` 出现 Restore complete。
2. 复制 `.env.example` 为 `.env`，填写 `LLM_API_KEY`、`LLM_MODEL`（可选 `LLM_BASE_URL`）。不需要额外 pip 包；有需要可使用 `python -m venv .venv`。
3. 回到项目根目录运行 `python agent.py`，输入问题；输入 `/confirm <proposal-id>` 执行已预览且明确确认的采购订单，`/quit` 退出。

## 设计

`agent.py` 的 `ERPNextClient` 提供通用元数据、计数、列表查询、详情读取和创建；`LLMRunner` 通过工具 schema 驱动模型；`Agent` 保留 proposal 状态机。所有相对日期以 `REFERENCE_DATE=2025-10-15` 计算，逾期按 `due_date < reference_date` 且 `outstanding_amount > 0` 判断。采购订单创建前校验 item、supplier、qty、uom、rate 和日期，展示预计总额；只有 `/confirm` 才写入，创建后回读。

## 验证

`python -m unittest discover -s tests -v` 验证日期规则、采购订单预览/确认、单位/日期校验和失败后防盲重试。真实 ERPNext API、真实 LLM E2E 和写入测试需在 Docker/密钥可用环境执行，结果写入 HANDOFF.md。
