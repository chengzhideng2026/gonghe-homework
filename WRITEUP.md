# WRITEUP 草稿

**工具边界。** Agent 暴露通用 `meta`、`list`（字段/过滤/分页/排序）、`get`（包含子表）和受控 `create`；业务答案由这些实时 API 证据组合而来，因此未知 DocType 不需要新增固定函数。

**不确定性。** 空结果会明确报告；ERP 权限/HTTP 错误保留为错误；歧义写操作必须先选择单据，不能自行取消。相对日期固定为 2025-10-15，逾期依据 due_date 和 outstanding_amount。

**写入路径。** Purchase Order 先实时校验供应商、物料、数量、单位、价格，生成 proposal 并展示明细/总额；只有用户输入 `/confirm <id>` 才 POST。创建后回读并显示名称和状态，ERP 校验错误可读化，超时不盲重试。

**可扩展性。** 新 DocType 只需复用 REST 工具和提示词/schema；客户端集中处理分页、字段、权限和错误。

**时间与范围。** 优先完成真实 API 工具和采购订单确认链，未做向量库、前端、多 Agent、云部署；当前机器缺 Docker，真实运行留给交接电脑。

**AI coding 工作流。** 使用 AI 生成初版结构，人工核对原始 README/DATASET、日期陷阱、API 路径和写入状态机；保留可审计 Git 历史。
