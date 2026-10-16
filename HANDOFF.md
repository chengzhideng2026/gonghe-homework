# 当前交接（审计后，2026-10-16）

活动工程：D:\work\工核homework。Docker数据在D盘，ERPNext运行于http://localhost:8080。Python标准库Agent在Windows主机运行，百炼qwen3.8-max已配置于本机.env。密钥未提交Git。

## 当前验证

- 29项代码测试通过，含跨页205行、并发领取、状态恢复、丢失写入回复、数值范围、受限算术、对话失败恢复等。
- 19项真实REST检查通过，Item=18、库存、采购、工单、发票等结果符合seed。
- 原题10问在七工具的新接口下重新运行，核心答案人工核对。
- 新增真实问答：应收余额$37,720、GreenAir $16,980；收款$58,990/付款$57,561/净流入$1,429；Nordic待交12/现货9/缺3。
- 完整应付聚合$22,784也由真实REST验证。
- 真实模型采购预览→SQLite保存→重建Agent后确认→POST→GET回读通过，单据PUR-ORD-2026-00029，Draft，$2,900，未提交。
- 真正的新Python进程重放同一确认被阻止，采购数量未再次增加。

## 数据库变化

保留两张测试草稿：00028为先前联调，00029为本轮审计。Purchase Order总数29；已提交开放采购单仍6张、$15,065.50。草稿没有改变库存。没有取消、删除、提交工单或采购单，没有重置数据库。

创建收据：evidence/test_po_receipt.json（00028），evidence/audit_write.json（00029）。后者存在时审计写入脚本拒绝重建；遇超时先对账，不删收据盲重跑。

## 文件入口

- ARCHITECTURE.md：完整架构、七工具、Docker职责、读写流程、业务陷阱、扩展与限制。
- AUDIT.md：本轮发现、修复、验证与交付清单。
- README.md：跨平台启动及CLI命令。
- WRITEUP.md：约一页设计/取舍/AI工作流程。
- evidence/llm_acceptance.json：最新十题真实轨迹；extended_audit.json为新增题；audit_restart_replay.json为新进程防重复证据。

## 使用与状态

在活动工程执行python agent.py即可。/pending查看保存预览，/confirm id确认，/discard id撤销本地预览，/reset清对话，/quit退出。交互状态在.local/proposals.sqlite3（Git与ZIP排除），API密钥只在.env。

API和CLI验证脚本有意分离：普通Agent(client)可用内存状态做隔离测试，交互CLI明确注入SQLite；verify_extended --create-test-po使用单独.local/audit-proposals.sqlite3，避免污染用户交互proposal。

原始ERP文件及备份未修改。Docker与百炼连接正常，未观察到防火墙弹窗。代码尚未上传GitHub，也没有向招聘方代发。后续仍需仓库上传、按原题复核运行流程及提交链接。

当前限制包括单行采购、本位币/stock_uom、无自动取消、不做税费事前试算、扫描非事务快照、无服务端全局幂等、模型解释仍需复核。详见架构文档。
