# Design Write-up — ERPNext Agent

**设计判断：让模型选择查询，让代码控制事实、计算与副作用。** ERPNext 是业务事实来源；模型没有通用 SQL、Shell 或直接创建订单的权限。实现为 Python 标准库 CLI，面向 [原题六项评审标准](ORIGINAL_README.md)。

## 1. Tool layer：通用读取 + 确定性计算

九个注册式工具分为三层：① 元数据、计数、列表、单单/批量详情、完整聚合；② `calculate` 与基于当轮真实 `evidence_ref` 的 `summarize_details`；③ 只生成本地采购预览的 `prepare_purchase_order`。

未知 DocType 先发现字段、Link/Table，再复用过滤、分页、父单和子表查询，不必增加一个专用工具。数值由 Decimal 计算，父单连接行与不同父单分别计数；币种、公司、单位分区；同一父单两次读取子表快照冲突则拒绝拼接。Schema、handler、effect/version 同源注册，Runner 不写死工具分发分支。

## 2. Uncertainty：只回答证据覆盖的范围

空结果、404、权限拒绝、字段错误、部分成功和分页未完成都不等于同一件事；`query_scope`、`complete` 与 `/trace` 暴露查询范围。业务日期固定 **2025-10-15**，不能按宿主时钟生成的发票 `status` 判定逾期；Bin 库存快照也不能证明历史转料。

程序提供有限小计与证据措辞检查，必要时要求模型改写一次；它**不是任意自然语言事实证明器**。失败轨迹保留，参见 [验收标准](BUSINESS_ACCEPTANCE.md)。

## 3. Write path：预览与实际写入分离

模型仅能请求生成单行、明确币种的采购预览；程序校验供应商、物料、UOM、金额、公司及日期，存入绑定连接的 SQLite 状态（15分钟有效）。用户必须独立输入 `/confirm <proposal_id>`；随后重新校验、原子领取、POST 草稿并 GET 回读。

丢失响应时保留操作状态与已知单号；`/reconcile` 只读核验，不盲目重发。此保证是**本地同一预览不重复派发**，不是 ERP 服务端跨机器 exactly-once。模型文本不能代替人工确认。

## 4. Extensibility：扩单据不扩模型权限

新只读 DocType 通常只需元数据发现与既有工具组合；确有新计算能力才在 `erp_tools.py` 注册 handler/Schema 并补契约测试。新写入类型必须另设业务校验与确认。ToolRegistry 接受可信代码，不是不可信插件沙箱或租户鉴权。

## 5. Judgment under constraints：优先修真正的业务风险

优先顺序是 **实时查询与完整性 → 口径/单位/币种 → 人工写入闸门 → 真实评测**。主动不做前端、Milvus、运行时多 Agent、云部署、多行/外币采购；它们不能优先解决这份题目的事实错误与采购副作用。

原题要求说明六小时投入。现有记录可复核开发阶段先后，但缺少可信的分阶段工时计量，因此**不编造“刚好六小时”时间表**，也不宣称满足六小时上限；详见 [AUDIT](AUDIT.md)。

## 6. Coding-agent workflow：隔离实施与验证

Codex 用于代码实现、测试生成和轨迹审阅；人为决定工具边界、写入权限与取舍。开发、独立业务评测、集成交付使用隔离工作区及固定 SHA，保留第一次失败，不用重测覆盖。

真实失败推动过两类改动：聚合来源正确而模型正文小计错误 → 本地 Decimal 小计和受限校验；子表误查耗尽 HTTP 预算 → 精确父端关联过滤与查询恢复。离线测试只证明程序契约，不等于模型回答正确率。

**证据边界**：原应用 `5fe679e` 有 170 项离线测试；九工具版 [PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2) 的 GitHub Actions 为 **190/190**。后续修复须按其提交 SHA 单独验收。隐藏题未知，仓库外报告不冒充公开证据。

启动、代码入口与完整限制见 [README](README.md)、[PROJECT_GUIDE](PROJECT_GUIDE.md)。
