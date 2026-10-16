# 当前交接（2026-10-17）

活动工程：D:\work\工核homework。Docker数据在D盘，ERPNext运行于http://localhost:8080。Python标准库Agent在Windows主机运行，百炼qwen3.8-max已有本机配置，密钥未提交Git。**当前免费额度已耗尽，模型请求返回HTTP403 `AllocationQuota.FreeTierOnly`；需要可用额度或有额度的密钥才能真实问答，不自动切付费。**

## 2026-10-17最新验证与待办

- 45项代码测试、19项真实REST复核通过。
- 修复重复聚合字段导致双计、非数组/非数值误处理，以及旧采购预览在ERP端点/凭据变化后仍可确认的问题；旧未绑定预览须重新准备。
- 新增`tool_receipts.py`、CLI `/trace`及列表强制`name`；实际工具收据可看查询、分页、错误和记录来源，但不是对最终回答的完整正确性证明。
- 八个新变式：7题正常返回且核心业务结果正确；完整回答E02/E05/E08通过，E01/E03/E04/E06部分通过，存在无证据额外断言；E07在19次工具调用后因免费额度耗尽未完成，不算通过。
- 8题采购单名称集合29→29，未创建新采购单。轨迹：`evidence/independent_variants_20261017.json`，案例与运行器：`review_cases.json`、`verify_variants.py`。
- 通用提示已调整为歧义先澄清、禁止无证据额外推断等，**额度耗尽后尚未真实复测**。恢复额度后优先复测部分通过题和E07；不把代码测试通过替代模型验收。
- 尚未上传GitHub或向招聘方提交链接；需本人理解并演示方案，不能保证面试结果。

## 2026-10-16验证（保留历史证据）

- 29项代码测试通过，含跨页205行、并发领取、状态恢复、丢失写入回复、数值范围、受限算术、对话失败恢复等。
- 19项真实REST检查通过，Item=18、库存、采购、工单、发票等结果符合seed。
- 原题10问在七工具的新接口下重新运行，核心答案人工核对。
- 新增真实问答：应收余额$37,720、GreenAir $16,980；收款$58,990/付款$57,561/净流入$1,429；Nordic待交12/现货9/缺3。
- 完整应付聚合$22,784也由真实REST验证。
- 真实模型采购预览→SQLite保存→重建Agent后确认→POST→GET回读通过，单据PUR-ORD-2026-00029，Draft，$2,900，未提交。
- 真正的新Python进程重放同一确认被阻止，采购数量未再次增加。

## 数据库变化

保留两张测试草稿：00028为先前联调，00029为2026-10-16审计。Purchase Order总数29；2026-10-17变式没有新增采购单。已提交开放采购单仍6张、$15,065.50。草稿没有改变库存。没有取消、删除、提交工单或采购单，没有重置数据库。

创建收据：evidence/test_po_receipt.json（00028），evidence/audit_write.json（00029）。后者存在时审计写入脚本拒绝重建；遇超时先对账，不删收据盲重跑。

## 文件入口

- ARCHITECTURE.md：完整架构、七工具、Docker职责、读写流程、业务陷阱、扩展与限制。
- AUDIT.md：本轮发现、修复、验证与交付清单。
- README.md：跨平台启动及CLI命令。
- WRITEUP.md：约一页设计/取舍/AI工作流程。
- TECH_REVIEW.md：隐藏题依据、SQLite与各层选型、替换条件、独立审查和面试讲解要点；[打开技术复核](TECH_REVIEW.md)。
- evidence/llm_acceptance.json：2026-10-16原题十问真实轨迹；extended_audit.json为当日新增题；audit_restart_replay.json为新进程防重复证据。
- evidence/independent_variants_20261017.json：2026-10-17八个独立变式轨迹及主审人工分级；包含HTTP403失败，不是八题全部通过的报告。

## 使用与状态

在活动工程执行python agent.py可启动CLI，但真实问答当前受免费额度耗尽阻断。/pending查看保存预览，/confirm id确认，/discard id撤销本地预览，/trace查看上一模型轮实际工具收据，/reset清对话，/quit退出。交互状态在.local/proposals.sqlite3（Git与ZIP排除），API密钥只在.env。`python agent.py --check`检查ERP和配置存在，不证明模型额度可用。

API和CLI验证脚本有意分离：普通Agent(client)可用内存状态做隔离测试，交互CLI明确注入SQLite；verify_extended --create-test-po使用单独.local/audit-proposals.sqlite3，避免污染用户交互proposal。

原始ERP文件及备份未修改。此前2026-10-16 Docker与百炼联调正常、未观察到防火墙弹窗；2026-10-17 ERP复核正常，但百炼因免费额度耗尽拒绝请求。代码尚未上传GitHub，也没有向招聘方代发。后续仍需恢复可用模型配置、真实复测、仓库上传、本人复核运行流程及提交链接。

当前限制包括单行采购、本位币/stock_uom、无自动取消、不做税费事前试算、扫描非事务快照、无服务端全局幂等、模型解释仍需复核。详见架构文档。
