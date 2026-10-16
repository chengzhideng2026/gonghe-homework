# HANDOFF

- 当前分支：master；最新 commit：待本阶段提交更新。
- 工作区：本阶段新增 agent.py、tests/、README.md、WRITEUP.md、.env.example、erpnext/，以及 ORIGINAL_README.md；`.env` 不应提交。
- 已完成：通用 ERPNext REST 客户端（meta/list/get/create、分页/过滤、错误处理）；固定参考日期和逾期规则；Purchase Order proposal/confirm/回读；本地单元测试；启动和设计文档。
- 未完成：Docker/ERPNext 真实 API smoke test（本机无 Docker）；真实 LLM 端到端（需填写 LLM_API_KEY 和 LLM_MODEL）；真实写入测试（会改变数据库）。已补上 OpenAI-compatible tool loop，尚未在本机执行。
- 入口：`agent.py`；`ERPNextClient` 和 `Agent`。
- 已执行（此前 Python 可用环境）：`python -m unittest discover -s tests` 通过；本轮当前环境无 python/py/docker 命令，无法复跑；Docker/ERPNext 未启动。
- 启动：复制 `.env.example` 为 `.env` 填 LLM 配置；`cd erpnext; docker compose up -d`；根目录 `python agent.py`。不要提交密钥。
- ERPNext：预期运行在本机 `http://localhost:8080`，当前未运行，数据库未被测试修改。
- 下一台电脑：安装 Docker Desktop 与 Python；启动并等待 restore-site；执行 `/api/method/frappe.client.get_count?doctype=Item` 预期 18；复制 `.env.example` 并填写 LLM_API_KEY/LLM_MODEL；运行 README 全部样例和变体验证；先用唯一 proposal 做确认写入，记录真实 PO 名称，必要时 `docker compose down -v` 恢复。
- 实际投入：约 1 小时（读取要求、脚手架、规则与文档）；后半程优先级：真实 API 验证 > LLM tool loop > 写入测试记录 > 细化错误和答案格式。


