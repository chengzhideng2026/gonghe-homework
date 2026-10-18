# Design Write-up — ERPNext Agent

**核心取舍：把业务事实、计算和写入权限交给可检查的代码；把语言理解与查询编排交给模型。** 不把 seed 数据答案塞进 Prompt，不让模型直接访问 SQL、Shell 或通用创建 API。实现为 Python 标准库 CLI，ERPNext 仍是唯一业务数据来源。

以下对应 [原题](ORIGINAL_README.md) 的六项评审要求；版本以 [`main-v2`](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2) 当前提交为准。

## 1. Tool layer — 通用读、确定性算、受控写

**模型可见九工具，但不是九个业务硬编码接口。**

- **通用发现与查询**：`get_doctype_meta`、`count_documents`、`list_documents`、`get_document`、`get_documents`、`aggregate_documents`。未知 DocType 可先发现字段/Link/Table，再用同一套过滤、分页、父单和子表读取；连接行与不同父单分别计数，失败与缺失保持不同语义。
- **有来源的计算**：`calculate` 用 Decimal 执行受限算术；`summarize_details` 只引用本轮真实父单读取结果的 `evidence_ref`，计算行数、金额、数量、极值与加权单价。跨公司、币种、单位不合并；同一父单重复读取出现不同子表快照则拒绝拼接。
- **唯一模型侧写入入口**：`prepare_purchase_order` 只生成本地预览，不执行 POST。工具 Schema、handler、effect 和版本在 `erp_tools.py` 同源注册；运行时视图由 `tool_registry.py` 管理，旧视图中的已撤销工具不能偷偷执行。

**为何不每种 DocType 一个工具？** 新单据通常是新元数据与查询组合，不是新函数；避免工具数量随表数量线性膨胀。特定业务计算只有在独立评测证明通用组合不够可靠时才值得加入。

## 2. Uncertainty — 范围、错误和业务口径不可混淆

查询成功但零条、指定单号404、权限拒绝、字段错误、部分批量成功、分页未完成，均有不同解释。 `query_scope` 与 `/trace` 记录实际过滤和数据来源；`complete=true` 只对其声明范围成立，不能推导业务类别全集。

特别处理 ERPNext 的时序与口径陷阱：业务参考日固定为 **2025-10-15**，不能直接按机器时间计算的发票 `status` 判断逾期；`outstanding_amount` 不是历史未付款证明；Bin 当前快照不能证明完成转料。已有有限的程序检查与一次改写/再失败拒答，但**不宣称能证明任意自然语言断言**。原始错误回答和修复证据保留在 [审计](AUDIT.md) 中。

## 3. Write path — 模型规划、人工授权、状态机执行

`prepare_purchase_order` 校验明确的供应商、物料、数量、UOM、单价/币种、公司及日期，生成绑定连接且15分钟有效的**本地**预览。只有用户键入 `/confirm <proposal_id>`，程序才复核数据、以 SQLite 事务原子领取预览、提交 ERP 草稿 POST，随后 GET 回读核验。

超时或丢失响应时保留本地状态与已知单号；`/reconcile` 只回读已有单号，**未知结果不盲目重发**。同一预览不会自动重复派发，但没有 ERP 服务端事务性幂等键，因此不宣称跨机器 exactly-once。模型无法调用 `/confirm`，文本里的“我已同意”不能替代用户实际确认。

## 4. Extensibility — 添加业务类型不重写 Runner

新只读单据：先用元数据发现并复用通用工具。新独立能力：在 `erp_tools.py` 添加 Schema + handler + 契约/业务边界测试；Runner 不需要增加按名称分支。新写入类型必须另设专属校验、审批与恢复策略。注册表只接收**可信宿主代码**，不是不可信插件沙箱，也不等于租户授权。

## 5. Judgment under six-hour constraint — 为什么主动做减法

优先级依次是：**真实数据与查询完整性 → 不确定性与单位/币种 → 写入安全 → 可复核评测**。保留 CLI、标准库与 SQLite；不做前端、RAG/Milvus、多 Agent、多模型路由、云部署、多行/外币采购，因为它们无法直接解决这份题目中更高风险的事实错误和副作用问题。

原题要求交代六小时内的时间分配。历史记录能证明先后阶段包括环境/数据探查、工具与采购路径、查询/安全回归、真实模型复测和交付文档，但**没有可靠的逐阶段工时记录**，因此不倒推出虚假的小时数，也不宣称实际完成时间满足六小时限制。具体历史见 [AUDIT](AUDIT.md)。

## 6. Coding agent workflow — AI 负责实施，证据决定合入

使用 Codex 辅助实现代码、生成测试、阅读运行轨迹与整理文档；人为决策工具边界、写入许可和修复优先级。开发、独立业务评测、上传集成分别采用隔离工作区和明确提交 SHA，保留首次失败而不是只展示重测成功。

**实际教训**：一次模型正确调用聚合工具，最终正文仍写错两个相互抵消的小计；另一次子表尝试重复失败导致过多 ERP GET。于是增加确定性小计来源、有限表格检查和更窄的父单过滤路径。Mock/离线测试只能验证程序契约，不替代真实模型业务准确率。

**证据界限**：原始 `5fe679e` 应用曾有 170 项离线测试；后续九工具合并版在 [PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2) 的 GitHub Actions 通过 **190 项离线测试**。任何后续修复均须另核对其 SHA 的测试与独立业务评测；公开仓库没有的报告不冒充已提交证据。原题隐藏测试未知，不承诺全通过。

更完整的代码地图、启动命令、验证入口和边界见 [README](README.md)、[PROJECT_GUIDE](PROJECT_GUIDE.md)、[BUSINESS_ACCEPTANCE](BUSINESS_ACCEPTANCE.md)。
