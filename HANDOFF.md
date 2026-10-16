# Windows 本机交接（2026-10-16）

## 活动项目与服务

- **后续请使用 `D:\work\工核homework`**。桌面原 ZIP 和 `_homework_review_20261016` 保留作来源，不是本轮修改的活动工程。
- Docker Desktop 4.95.0，Engine 29.8.2，Compose v5.6.0；WSL2 后端，Ubuntu 集成已开。
- GUI 确认磁盘目录为 `D:\DockerData\DockerDesktopWSL`；不需要迁移。
- Python 3.13.0；Agent 只用标准库，不依赖 pip 包。
- 原始 ERPNext `compose.yml`、DATASET、备份和原始题目未修改。
- `docker compose up -d` 已完成；restore-site 退出码 0，日志出现 **Restore complete.**。
- 服务正在运行，页面 http://localhost:8080 已在 Chrome 打开；本地登录 Administrator / admin。
- `.env` 已由样例创建，包含本地 ERP 连接参数，**LLM_API_KEY 与 LLM_MODEL 仍空白**。不把真实密钥发到聊天或提交 Git。

## 本轮真实验收

| 范围 | 结果 | 证据 |
|---|---|---|
| 物料数 | 18 | evidence/live_read.json |
| 铜线库存 | Stores - CCM：现有 50、在途 200、生产预留 60 Meter | 同上 |
| 开放采购单 | 6 张，合计 $15,065.50 | 同上 |
| 客户订单排名 | GreenAir 5 张，Summit 4 张，覆盖全部 25 张订单 | 同上 |
| 工单 MFG-WO-2026-00020 | 电机需30有20、泵需30有20、铜线需60有50 | 同上 |
| 1HP/R32 毛利基础 | BOM成本 $575.20、标准售价 $600，可计算毛利 $24.80 / 4.13% | 同上（基础值检查） |
| 逾期应收 | 按 2025-10-15，4 张合计 $25,380，排除未到期单据 | 同上 |
| 无数据与歧义 | laptop 无物料、Employee=0、两张开放工单候选 | 同上（工具结果；模型行为待验） |
| 元数据 | 真实主表及子表 schema，去除界面脚本 | verify_live.py 与真实API |
| 采购预览 | $2,900，固定日期、预览不写库 | evidence/live_read.json |
| 采购创建及回读 | 已创建且回读，重复确认被拒绝 | evidence/live_write.json、test_po_receipt.json |
| 单元回归 | 11/11，通过 HTTP 传输、确认、异常恢复等检查 | tests/ |
| 真实模型问答 | **未执行：缺少模型配置**，不能将 REST 检查当作模型 E2E | verify_llm.py 已准备 |

## 数据库变化（必须知悉）

本轮仅新增一张本地测试采购草稿：

- 单号：**PUR-ORD-2026-00028**。
- Supplier：Tongling Magnet Wire Co.；物料 RM-COIL-CU-2.0；100 Meter × $29。
- grand_total：2900；docstatus=0；status=Draft；transaction_date / schedule_date 均为 2025-10-15。
- 创建前 Purchase Order 共27张，创建后28张；原有6张开放已提交采购单总额保持不变，草稿不改变库存。
- 没有提交、取消或删除业务单据，没有重置数据库卷。
- 测试脚本保留收据；已有收据时禁止再次写入。请求超时也不能盲目重跑。

## 本轮修复

1. REST 路径编码 DocType 和单号，解决 Purchase Order / Sales Invoice 等名称的空格问题，并保护单号中的斜杠、#。
2. .env 从脚本旁读取，避免换工作目录后找不到配置。
3. 拒绝 NaN/Infinity 数量、单价。
4. 创建成功但回读失败时明确显示单号，锁定 proposal 防重复创建。
5. CLI 独立输出准确采购载荷和确认命令，不依赖模型复述；用户确认结果写入对话历史；提示词要求完整分页和统计口径，禁止把业务字段文字当指令。
6. 元数据由约513KB精简至约29KB，保留7个采购主子表数据结构，去除界面脚本和布局。
7. 新增 Windows 启动脚本、只读/显式写入验收和模型问答轨迹脚本；保留原 Git 历史。

## 你回来后继续

1. 在本机 `.env` 填写实际服务商的 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL（需支持 Chat Completions 的工具调用）。
2. `python agent.py --check` 确认 item_count=18 且 llm_configured=true。
3. `python agent.py` 交互问答，或 `python verify_llm.py` 保存全部样例问答和工具轨迹（会调用收费API）。
4. 人工逐条核对 `evidence/llm_acceptance.json` 的答案、日期、无数据和澄清行为。该脚本不确认采购，不会再创建订单。
5. 模型验收后将工程推送到自己的新 GitHub 仓库，发送链接完成提交。当前没有配置 Git remote，也没有上传或代发给招聘方。

## 能力边界

真实 REST、预览和本地草稿写入已通过；真实 LLM 工具选择、多轮回答及未知问题正确性仍待验证。proposal 状态仅在进程内，不提供持久化跨会话幂等；不支持取消工单。不要把本地 seed 凭据用于生产环境。
