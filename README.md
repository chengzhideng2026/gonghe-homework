# Plantcore ERPNext Agent

**基于真实 ERPNext API 的工业业务 Agent：可追溯查询、确定性统计、受控采购。**

本项目使用 Python 标准库实现 CLI 与模型工具循环，连接题目提供的 Crestwind Compressor Manufacturing Co.（CCM）ERPNext。Agent 能查询库存、采购/销售订单、工单、BOM 和发票；处理未知 DocType 与父子表关联；计算有来源的小计；并在用户**独立确认后**创建采购草稿。业务参考日固定为 **2025-10-15**，不以机器时钟或单号年份替代。

**设计原则：业务事实从 ERP 读取，计算与权限约束由代码执行，模型负责理解问题和选择工具。** 不把 `DATASET.md` 中的答案装进模型提示，也不开放 SQL、Shell 或通用写入工具。

**工程验证与业务评测（按版本区分）**

| 已验证的结果 | 适用范围 |
|---|---|
| **190 / 190** 离线回归通过 | 当前已交付 `main-v2`，见 [合并 PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2) |
| **205 / 205** 离线回归通过 | [定向修复 PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4) 的候选 SHA `571f52e`，**尚未合并；真实性能与 FNL-12 待复测** |
| 多系列真实 ERP + 模型历史评测 | E/H/C 等已保存原始轨迹、部分失败和复测结论；详见 [评测证据索引](EVALUATION_EVIDENCE.md)，不能拼成一个最终版本的通过率 |
| **60 题统一评测** | 40 道去重历史候选题 + 20 道新题，**规划中，未冻结 Oracle、未执行，不展示通过率** |

这些数字分属代码级回归和真实模型业务评测，不可互相代替。

## 1. 快速启动

需要 Git、Python **3.10+**、Docker Engine/Desktop、Compose **2.24.4+** 及可用的 OpenAI-compatible 模型 API。Agent 自身无需第三方 Python 包；首次下载镜像、ERP 恢复和模型配置可能使总启动时间超过五分钟。

在终端执行：

```bash
git clone --branch main-v2 https://github.com/chengzhideng2026/gonghe-homework.git
cd gonghe-homework

# 从项目根目录启动题目 ERPNext（端口仅绑定本机回环）
docker compose -f erpnext/compose.yml -f compose.local.yml up -d
docker compose -f erpnext/compose.yml -f compose.local.yml logs -f restore-site
```

首次恢复看到 `Restore complete.` 后按 Ctrl+C 退出日志查看（不是停止容器）。已存在的站点可能跳过恢复。ERP 管理页面：http://localhost:8080；题目 seed 的演示账户见 [原题](ORIGINAL_README.md)。**不要为了普通重启执行 `docker compose down -v`，那会删除数据卷。**

仅当项目根目录没有 `.env` 时，复制示例文件：

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

在本地 `.env` 中填写模型服务的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`；核对 `ERPNEXT_URL`、`ERPNEXT_API_KEY`、`ERPNEXT_API_SECRET`。题目 seed 提供了 ERP API 的演示配置。**不要提交真实密钥或 `.env`。**

```bash
python agent.py --demo         # 加载检查：无需模型/ERP
python agent.py --check        # ERP 连接 + 模型配置检查：不调用模型
python agent.py                # 进入交互式 Agent
```

`python agent.py --check-model` 为可选的真实模型与只读工具协议检查，会消耗模型额度；它不代表业务题已验收。Linux/macOS 可按环境将 `python` 改为 `python3`。

## 2. 三个评审场景

以下问题可直接输入到 `python agent.py`。请用 `/trace` 核对实际工具调用、过滤范围、分页与数值来源；不同 ERP 状态下以实时读取为准。

| 场景 | 推荐问题 | 评审重点 |
|---|---|---|
| 库存与跨轮计算 | “铜线的现货、在途和生产预留分别是多少？列出物料、仓库、单位。”随后问：“以刚才同一物料及仓库的现货为依据，目标 180 Meter，缺口是多少？” | 实物与在途不混算；沿用正确物料身份；单位一致；计算留有来源 |
| 参考日期与财务 | “以 2025-10-15 为参考日，列出已提交、尚未付清且已逾期的销售发票，包含币种、到期日、未结余额。” | 按日期字段判断，而不是直接相信宿主时钟生成的原始 `status` |
| 采购预览（不写 ERP） | “按已核验的供应商、物料、数量、单位、单价/币种和日期，仅准备一张采购草稿预览，不执行创建。” | 本地预览与 ERP 实际单据分离；必须人工 `/confirm <proposal_id>` 才能创建 |

`/pending` 查看本地预览，`/discard <proposal_id>` 放弃预览，`/reconcile <proposal_id>` 只读核查已记录单号；`/quit` 退出。预览默认有效期 15 分钟，并绑定 ERP 连接配置。**预览成功不表示订单已创建。** 不建议在只读评审中输入 `/confirm`。

## 3. 为什么采用这套架构

| 设计选择 | 解决的业务风险 |
|---|---|
| **9 个注册式工具**：元数据、计数、列表、单单/批量详情、完整聚合、Decimal 算术、明细统计、采购预览 | 未知 DocType 先发现结构再查询；Schema 与执行 handler 同源；模型不能调用任意代码 |
| **来源与完整性**：`query_scope`、分页、父单去重、部分失败、`/trace` | 防止把子表连接行数当父单数、把空结果当接口错误、把部分结果称作全量 |
| **确定性数值**：`aggregate_documents`、`calculate`、`summarize_details` | 避免模型手算造成小计和加权统计错误；金额按公司/币种、数量按单位区分 |
| **证据绑定明细**：仅引用当前轮真实 `get_document(s)` 读取的 `evidence_ref` | 不让模型自行提交虚构数值；同一父单两次读取的子表快照不一致时拒绝拼接 |
| **独立写入闸门**：本地 SQLite 预览 → 用户 `/confirm` → ERP POST → GET 回读 | 模型不能自行授权采购；未知提交结果不盲目重发；支持已知单号只读对账 |

新增只读业务类型通常无需新增工具；新业务能力可在 [`erp_tools.py`](erp_tools.py) 注册 Schema、handler 与契约测试。涉及写入的能力必须另设专用校验与人工确认，不应由通用工具绕过。

## 4. 验证与证据边界

- **当前已合并应用版本**：`main-v2` 的 [PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2) 经 GitHub Actions **190/190 项离线测试通过**；当前分支后续如有新提交，以对应 SHA 的实际 CI 结果为准。历史真实模型业务题并非只有最新12题，按系列、结果及版本边界整理于 [评测证据索引](EVALUATION_EVIDENCE.md)。
- **原始应用基线**：`5fe679e` 曾通过 170 项代码测试、248 项子测试和 `--demo`；此成绩不可自动套用到后续版本。
- **真实业务评测**：已有开发复测、独立变式和失败回放；结果、原始轨迹及适用 SHA 必须分别对照 [业务验收说明](BUSINESS_ACCEPTANCE.md) 与 [历史审计](AUDIT.md)。仓库外的独立运行文件不冒充公开可下载证据。
- **安全界限**：模型没有直接 ERP 写工具；`/confirm` 的写入回路有专门代码与测试，但现有用户手动演示到采购**预览**为止。单机 SQLite 幂等不等于 ERP 服务端 exactly-once。

运行离线回归：

```bash
python -m unittest discover -s tests -v
```

离线单测不是实际模型回答正确率；一次模型案例成功也不是隐藏题保证。系统仍有开放问题：当前轮超大工具响应、自然语言中未受结构化检查覆盖的附加断言、上游分页/事务快照完整性、多行/外币采购及生产环境租户授权。这些限制不会被 `complete=true`、`temperature=0` 或较高的测试数掩盖。

## 5. 设计与深入资料

- **先看**：[一页设计说明](WRITEUP.md)（按原题六项评审指标组织）· [原始作业要求](ORIGINAL_README.md)
- **代码与操作**：[项目接手指南](PROJECT_GUIDE.md) · [工具注册](TOOL_REGISTRY.md) · [架构](ARCHITECTURE.md)
- **正确性与安全**：[业务验收](BUSINESS_ACCEPTANCE.md) · [请求成本](API_EFFICIENCY.md) · [采购恢复设计](RECOVERY_AND_DESIGN.md)
- **历史证据**：[评测证据索引](EVALUATION_EVIDENCE.md) · [审计记录](AUDIT.md) · [原始明细统计实验](https://github.com/chengzhideng2026/gonghe-homework/tree/experiment/detail-statistics/experiment)

**评审入口始终是公开仓库默认分支 [`main-v2`](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2)**；其他实验及待审 PR 不代表已交付能力。
