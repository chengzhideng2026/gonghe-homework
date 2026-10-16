# HANDOFF

- 当前分支：master；最新 commit：以 `git log -1 --oneline` 为准。
- 工作区：本阶段修改 agent.py、requirements.txt、tests/test_agent.py、HANDOFF.md；`.env` 不应提交。原始说明保留在 `ORIGINAL_README.md`，ERPNext seed stack 在 `erpnext/`。
- 已完成：通用 ERPNext REST 客户端（meta/list/get/count/create、字段/过滤/分页/排序、错误包装）；OpenAI-compatible chat-completions tool loop；固定参考日期和逾期规则；Purchase Order 预览→显式 `/confirm <id>`→创建→回读；Item/Supplier/UOM/日期校验；预览使用深拷贝快照，修改预览不会改变待写入内容；创建失败或超时禁止盲重试；本地 fake-client 单元测试。
- 未完成：Docker/ERPNext 真实 API smoke test（本机没有 Docker/Compose，8080 未监听）；真实 LLM E2E（需填写 LLM_API_KEY 和 LLM_MODEL）；真实 Purchase Order 写入（会改变数据库）；README 全部样例的真实 API 验证。
- 入口：`agent.py`；`ERPNextClient`、`Agent`、`LLMRunner`。运行时只依赖 Python 标准库；`.env` 由内置 loader 读取。
- 已执行：`C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q agent.py tests` 通过；同一解释器 `-m unittest discover -s tests -v` 通过（7 tests）；`agent.py --demo` 通过；`git diff --check` 通过。未执行且不可声称通过：Docker restore、Item=18 API、真实 LLM、真实写入。
- 启动：复制 `.env.example` 为 `.env`，填写 LLM_API_KEY、LLM_MODEL、可选 LLM_BASE_URL；`cd erpnext; docker compose up -d`；等待 `docker compose logs -f restore-site` 出现 Restore complete；回到根目录执行 `python agent.py`。不要提交密钥。
- ERPNext：目标为本机 `http://localhost:8080`，当前未启动，数据库未被本次测试修改。Item 冒烟：`curl -fs -H "Authorization: token crestwind-agent:crestwind-agent-secret" "http://localhost:8080/api/method/frappe.client.get_count?doctype=Item"`，预期 `18`。
- 下一台电脑：安装 Docker Desktop、Python；启动并等待 restore-site；先做 Item=18，再运行 README 全部样例和同类变体验证；填写 LLM 配置后运行真实多轮查询；用测试供应商/物料创建唯一 PO，记录真实单据名、状态和回读结果；回读/创建超时先人工查 ERPNext，禁止重试；必要时 `docker compose down -v` 恢复干净数据库。
- 实际投入：约 2 小时（读取要求、实现客户端/工具 loop/确认状态机、补单测和文档）；后半程优先级：真实 API 验证 > 真实 LLM 样例 > 写入测试记录 > 结果整理。





