# 项目交接

活动工程是解压或 clone 后的项目根目录。ERPNext 默认入口为 [localhost:8080](http://localhost:8080)，Agent 在主机 Python 进程运行，模型经云端 API 调用。私有配置保留在本机 `.env`，不提交 Git。接手操作请先读 [PROJECT_GUIDE.md](PROJECT_GUIDE.md)，当前运行入口见 [README](README.md)。

## 当前状态

- 用户充值后模型 API 已恢复，E07 探测在 10.67 秒内正常返回澄清。此前免费额度 HTTP403 是已保留的历史失败，不是当前阻断。
- 54 项代码测试、19 项真实 REST 再次复核通过；从非项目目录使用脚本绝对路径运行 `--check` 也通过。已修复重复聚合/参数类型、预览 ERP 端点与凭据绑定，并新增 `/trace`、列表 name、query_scope、Bin 快照警告和受限回答检查。
- 充值后完整八题复跑：核心 8/8，完整回答 6 通过、2 部分。E01 附带无凭证历史与额外公式，E07 把关键词候选当成业务类别全集，均未按完整正确处理。
- 补充查询范围与快照警告后，定向复测 E07 通过，E01 仍部分。再加入 `answer_checks.py` 后，E01 不再有历史断言，但附加 130+100 公式未调用 calculate，保守仍部分；E07 通过。该实模运行未触发门禁修正，不能说真实修正链路已经触发过；机制由 mock 测试验证。
- 三轮真实对话完成：Stores 实物 130 Nos、在途 100 → 目标 180、现货缺口 50（调用 calculate）→ 引用上轮 50 Nos 按 USD4.20 生成 USD210 预览。核心与载荷断言通过；第二轮额外在途情景公式未调用工具，整段部分。
- 本轮所有复测前后采购单名称集合均为本地 29→29，没有新建 ERP 采购单。该数量不是 fresh seed 的运行前提。
- 尚未上传 GitHub 或提交招聘方链接；仍需本人跑通并解释方案，不保证隐藏题或面试结果。

## 最新证据入口

| 文件 | 内容 |
|---|---|
| `evidence/recharge_check.json` | 充值后 E07 可用性与澄清探测 |
| `evidence/variants_followup.json` | 充值后完整八题复跑，需结合人工分级 |
| `evidence/variants_refined.json` | 加 query_scope 与 Bin 警告后的定向复测 |
| `evidence/variants_checked.json` | 加受限回答检查后的定向复测；实际没有触发修正 |
| `evidence/conversation_check.json` | 三轮库存→缺口→采购预览与未写检查 |
| `evidence/VARIANT_REVIEW.md`、`AUDIT.md` | 主审人工分级与完整演进记录 |
| [evidence/FOLLOWUP_REVIEW.md](evidence/FOLLOWUP_REVIEW.md) | 充值后完整复跑、定向与三轮会话的最新人工总判分 |

`variants_initial.json` 保留最初 3 通过、4 部分、1 额度阻断的运行，不能作为当前 API 不可用的依据。后续改进没有覆盖全部新问法，也未把所有额外公式检查变成硬约束。

## 已有真实写入证据与本地数据

2026-10-16 及此前的审计创建了两张本地测试草稿：00028、00029；其中 `PUR-ORD-2026-00029` 为 USD2,900、Draft、未提交。相关收据为 `test_po_receipt.json`、`audit_write.json`；`audit_restart_replay.json` 记录新 Python 进程重复确认被阻止。

本地采购单总数 29，已提交开放采购仍 6 张、USD15,065.50。草稿没有改变库存；本轮没有取消、删除、提交采购或工单，也没有重置数据卷。不要删除写入收据或日志来重复测试创建。

当日历史验证包含 29 项代码测试、19 项 REST、原题十问和应收/净额/缺货新增题；这些历史数字与记录保留，当前代码测试数量以最新输出为准。

## 操作与恢复

`python agent.py` 启动 CLI。`/trace` 看上一模型轮实际工具收据；`/pending` 看预览；`/confirm id` 对具体载荷确认并创建草稿；`/discard id` 只撤销本地预览；`/reset` 只清会话；`/quit` 退出。`--check`只证明 ERP 与配置存在，不验证 API 额度或回答质量。

交互状态在 `.local/proposals.sqlite3`。普通 `Agent(client)` 可使用内存状态隔离测试；历史可选写入验证使用独立 journal。预览过期、目标配置变化须重新准备；creating/failed 或回读失败先按单号对账，不能盲重发。

`/trace` 和 `query_scope` 显示查过什么、按什么过滤；关键词候选不证明类别全集，Bin 位置不证明历史转料。受限门禁只覆盖已知措辞，可请求改写一次或拒绝，不能保证所有最终文字正确。

## 后续优先级

先由本人按接手指南完成查询、证据核对、预览与状态恢复练习，再整理提交仓库和链接。继续改进时优先解决无必要额外公式和算术工具使用的一致性，并保留新案例证据；不为技术名词而更换 SQLite 或堆叠框架。

详细架构见 [ARCHITECTURE.md](ARCHITECTURE.md)，选型与隐藏题说明见 [TECH_REVIEW.md](TECH_REVIEW.md)。单行/本位币/stock_uom、无自动取消、非事务扫描、无服务端全局幂等与生产权限隔离等边界仍保留。
