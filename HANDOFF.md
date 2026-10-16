# HANDOFF

- 当前分支：master；最新 commit：以 `git log -1 --oneline` 为准。
- 工作区：本阶段更新 README.md、WRITEUP.md、HANDOFF.md；`.env` 不应提交。原始说明保留在 `ORIGINAL_README.md`，ERPNext seed stack 在 `erpnext/`。
- 原始文件核对：桌面 ZIP `C:\Users\HP\Desktop\plantcore_erp_seed_homework2026-10.zip` 与 `ORIGINAL_README.md`、`erpnext/DATASET.md`、`erpnext/compose.yml`、`erpnext/.env.example` 内容一致；根目录 `.env.example` 是新增 Agent 配置文件，差异是有意的。
- 已完成：通用 ERPNext REST 客户端（meta/list/get/count/create、字段/过滤/分页/排序、错误包装）；OpenAI-compatible chat-completions tool loop；固定参考日期和逾期规则；Purchase Order 预览→显式 `/confirm <id>`→创建→回读；Item/Supplier/UOM/日期校验；预览使用深拷贝快照；创建失败或超时禁止盲重试；本地 fake-client 单元测试。
- 环境检查：Windows 10 Home China；`docker version`、`docker compose version`、`docker info` 均因 `docker` 命令不存在而失败；Docker Desktop 路径和服务不存在；8080/8000 无监听。`wsl.exe` 存在但 `wsl --status`/`wsl -l -v` 显示安装提示、没有发行版。检查 Windows 可选功能和 CPU 虚拟化需要管理员权限，当前返回 Access denied，未能判定 BIOS 虚拟化状态。
- 未完成：Docker/ERPNext restore 和 Item=18 smoke；真实 ERPNext API 查询；真实 LLM E2E；README 全部样例查询；真实 Purchase Order 写入。数据库未被本阶段真实测试修改，未产生测试单据。
- 本地已执行：`C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q agent.py tests`、`-m unittest discover -s tests -v`（7 tests）、`agent.py --demo`、`git diff --check`，均通过。上述均不是 ERPNext/LLM 端到端测试。

## 验收表（当前阶段）

| 场景 | 实际结果 | 状态 | 依据 |
|---|---|---|---|
| Docker/restore-site | docker 命令不存在 | 未验证 | 环境检查错误 |
| Item 数量=18 | ERP 未启动 | 未验证 | 无 8080 服务 |
| 库存/开放 PO/客户订单数 | 未调用真实 API | 未验证 | 需 Docker |
| 工单缺料/毛利/逾期发票 | 未调用真实 API/LLM | 未验证 | 需 Docker+模型 |
| 缺失物料/员工数据/取消工单歧义 | 仅工具设计，未 E2E | 未验证 | 需 Docker+模型 |
| PO 100m × $29 预览 | fake-client 单测通过 | 部分验证 | 未写真实数据库 |
| PO 明确确认后创建/回读 | fake-client 单测通过 | 未验证 | 未写真实数据库 |
| 重复确认/创建异常防盲重试 | fake-client 单测通过 | 部分验证 | 真实网络超时未测 |

## 下一台电脑复现

1. 保存当前工作并安装/启用 WSL2：管理员 PowerShell 执行 `wsl --install`，按提示重启；必要时在 BIOS 开启 VT-x/AMD-V。
2. 安装 Docker Desktop，选择 WSL2 backend，启动后重新打开终端。
3. 执行 `docker version`（必须同时有 Client/Server）和 `docker compose version`。
4. `cd C:\Users\HP\Documents\ChatGPT\工核homework\erpnext; docker compose up -d`；`docker compose logs -f restore-site` 等待 `Restore complete.`。
5. 用 token 请求 `http://localhost:8080/api/method/frappe.client.get_count?doctype=Item`，确认返回 18。
6. 根目录复制 `.env.example` 为 `.env`，只在本机填写 `LLM_API_KEY`、`LLM_MODEL`、必要时修改 `LLM_BASE_URL`；运行 `python agent.py`。
7. 逐条执行原始 README 查询并保存真实响应依据；先验证 PO 预览无写入，再用 `/confirm <proposal-id>` 创建唯一测试 PO，记录真实名称、状态、回读内容和数据库是否改变。
8. 若创建请求超时，先在 ERPNext 查询同一供应商/物料/日期的 PO，禁止直接重试；必要时 `docker compose down -v && docker compose up -d` 恢复干净 seed 数据。

- 实际投入：约 2.5 小时；后半程优先级：安装并验证 Docker > Item=18/API > 真实 LLM 样例 > 真实 PO 写入 > 整理证据。
