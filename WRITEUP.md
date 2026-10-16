# WRITEUP 草稿

**工具边界。** Agent 暴露通用 `meta`、`count`、`list`（字段/过滤/分页/排序）、`get`（包含子表）和受控 `create` 客户端；LLM 实际可调用的工具只有元数据、计数、列表、详情和 `prepare_purchase_order`。没有把直接创建工具暴露给模型，写入只由 CLI `/confirm <proposal-id>` 触发。未知 DocType 不需要新增固定函数。

**不确定性。** 空结果会明确报告；ERP 权限/HTTP 错误保留为错误；歧义写操作必须先选择单据，不能自行取消。相对日期固定为 2025-10-15，逾期依据 due_date 和 outstanding_amount。真实 ERPNext/LLM 联调尚未执行，不能把 mock 结果当作端到端结论。

**写入路径。** Purchase Order 先实时校验供应商、物料、数量、单位、价格和日期，生成 proposal 并展示明细/总额；只有用户输入 `/confirm <id>` 才 POST。proposal 存储深拷贝，修改展示对象不会改变待写入快照；创建后回读并显示名称和状态。创建异常会锁定 proposal 并提示人工核查，避免盲目重试。真实写入单据尚未产生。

**可扩展性。** 新 DocType 只需复用 REST 工具和提示词/schema；客户端集中处理分页、字段、权限和错误。

**时间与范围。** 优先完成真实 API 工具和采购订单确认链，未做向量库、前端、多 Agent、云部署。当前开发机缺 Docker/WSL 配置，真实联调被环境阻塞；未通过修改业务代码掩盖该阻塞。实际投入约 2.5 小时，后续优先级是安装并验证 Docker、执行 Item=18 smoke，再做真实 LLM 和写入验收。

**Coding agent workflow.** 使用 AI 生成初版结构，人工核对原始 README/DATASET、日期陷阱、API 路径和写入状态机；通过 fake-client 单测验证状态转换；保留可审计 Git 历史。真实模型和 ERPNext 联调仍待在有 Docker 和本地模型密钥的机器完成。
