# HANDOFF

- 当前分支：master；最新 commit：见 `git log -1 --oneline`。
- 工作区：本阶段新增 agent.py、tests/、README.md、WRITEUP.md、.env.example、erpnext/，以及 ORIGINAL_README.md；`.env` 不应提交。
- 已完成：通用 ERPNext REST 客户端（meta/list/get/create、分页/过滤、错误处理）；固定参考日期和逾期规则；Purchase Order proposal/confirm/回读；本地单元测试；启动和设计文档。
- 未完成：Docker/ERPNext 真实 API smoke test；真实 LLM 端到端编排；真实写入测试（会改变数据库）；更完整的自然语言工具选择。
- 入口：`agent.py`；`ERPNextClient` 和 `Agent`。
- 已执行：`python -m unittest discover -s tests`（应通过）；Docker 命令检查失败：本机未安装/不可用 Docker，故 ERPNext 未启动。
- 启动：复制 `.env.example` 为 `.env` 填 LLM 配置；`cd erpnext; docker compose up -d`；根目录 `python agent.py`。不要提交密钥。
- ERPNext：预期运行在本机 `http://localhost:8080`，当前未运行，数据库未被测试修改。
- 下一台电脑：安装 Docker Desktop；启动并等待 restore-site；执行 `/api/method/frappe.client.get_count?doctype=Item` 预期 18；运行 README 全部样例和变体验证；配置 LLM 后完成工具编排；先用唯一 proposal 做确认写入，记录真实 PO 名称，必要时 `docker compose down -v` 恢复。
- 实际投入：约 1 小时（读取要求、脚手架、规则与文档）；后半程优先级：真实 API 验证 > LLM tool loop > 写入测试记录 > 细化错误和答案格式。
