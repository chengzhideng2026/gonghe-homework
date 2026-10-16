# Windows 本机交接（2026-10-16）

## 活动项目与服务

- **后续请使用 `D:\work\工核homework`**。桌面原 ZIP 和 `_homework_review_20261016` 保留作来源，不是本轮修改的活动工程。
- Docker Desktop 4.95.0，Engine 29.8.2，Compose v5.6.0；WSL2 后端，Ubuntu 集成已开。
- GUI 确认磁盘目录为 `D:\DockerData\DockerDesktopWSL`；不需要迁移。
- Python 3.13.0；Agent 只用标准库，不依赖 pip 包。
- 原始 ERPNext `compose.yml`、DATASET、备份和原始题目未修改。
- `docker compose up -d` 已完成；restore-site 退出码 0，日志出现 **Restore complete.**。
- 服务正在运行，页面 http://localhost:8080 已在 Chrome 打开；本地登录 Administrator / admin。
- `.env` 已由样例创建，包含本地 ERP 连接参数，**已配置百炼 qwen3.8-max，思考模式开启**。不把真实密钥发到聊天或提交 Git。

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
| 无数据与歧义 | laptop 无物料、Employee=0、两张开放工单候选 | 同上（工具结果；模型行为已实测） |
| 元数据 | 真实主表及子表 schema，去除界面脚本 | verify_live.py 与真实API |
| 采购预览 | $2,900，固定日期、预览不写库 | evidence/live_read.json |
| 采购创建及回读 | 已创建且回读，重复确认被拒绝 | evidence/live_write.json、test_po_receipt.json |
| 单元回归 | 14/14，通过 HTTP 传输、确认、异常恢复等检查 | tests/ |
| 真实模型问答 | 百炼 qwen3.8-max 思考模式，10个样例已真实执行，最终主要求逐题核对 | evidence/llm_acceptance.json、LLM_REVIEW.md |

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

## 你回来后使用

1. `.env` 已配置，无需再次填写密钥。执行 `python agent.py --check` 可检查 ERP 与配置。
2. 执行 `python agent.py` 开始交互，中文和英文均已实测。`/quit` 退出。
3. `python verify_llm.py` 可重新保存十个原题问答和工具轨迹；不确认采购，因此不会增加单据。
4. 最终模型样例检查见 LLM_REVIEW.md。诊断阶段的 initial/probe 文件保留用于说明修复过程，验收以最终结果为准。
5. 后续尚需选择 GitHub 仓库并上传，再将链接提交招聘方。当前没有上传或代发。

## 能力边界

真实 REST、真实 LLM 十个样例、中文多轮、预览以及本地草稿写入均已实测。样例通过不代表未知问题全部正确，仍需独立留出题和人工复核。proposal 状态仅在进程内，不提供持久化跨会话幂等；不支持取消工单。不要把本地 seed 凭据用于生产环境。

## API 联调补充

- 百炼北京地域兼容接口已实际连通，模型 qwen3.8-max，enable_thinking=true，thinking_budget=4096。
- 工具循环由8轮增至可配置16轮，请求超时可配置180秒；完整批次初跑每题2–5轮、工具错误0；含专项复测的最终结果每题2–8轮，有1次字段错误后自行恢复。
- 修复单条过滤条件扁平数组导致 ERPNext 误报 DocType i 不存在的问题；过滤结构规范化并增加回归测试。
- 修复 Windows GBK 控制台打印模型 Unicode 符号报错；CLI 和模型验收脚本统一 UTF-8。
- 对无答案/无工具和截断输出显式报错，保留真实工具消息与模型上下文。
- 当前未观察到 Docker 防火墙弹窗；本地ERP和百炼调用已正常，不需要修改防火墙。
- 本轮模型测试只预览采购，没有新增/提交/取消采购或工单；采购总数仍28。
