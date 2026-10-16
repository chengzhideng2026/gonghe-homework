# Plantcore ERPNext Agent

一个Python标准库CLI Agent：用阿里百炼/兼容Chat Completions的模型选择工具，通过ERPNext实时HTTP API读业务数据。包含原题ERP seed与连续Git历史，原题全文见 ORIGINAL_README.md。

## 五分钟启动流程

前提：Python 3.10+、Docker Desktop/Engine及Compose可用。首次镜像下载和站点恢复可能超过五分钟；本机已缓存并恢复完毕。无需pip安装。先进入解压/clone后的项目根目录（本机是 `D:\work\工核homework`）。

```text
docker compose -f erpnext/compose.yml up -d
docker compose -f erpnext/compose.yml logs -f restore-site
```

首次等待 `Restore complete.`；后续启动可能显示站点已存在并跳过恢复。Ctrl+C只退出日志查看。

第一次复制配置：Windows PowerShell使用 `Copy-Item .env.example .env`；Linux/macOS使用 `cp .env.example .env`。在本机.env填写模型API密钥；样例已默认qwen3.8-max与百炼北京地域地址。如果换服务商，同时调整模型、地址与思考参数。不要覆盖已有.env。

```text
python agent.py --check
python agent.py
```

Linux上若命令名为python3，替换为python3。ERPNEXT Item数量应为18；--check只检查ERP连接和配置是否存在，不宣称验证模型质量。本机.env已经配置，可直接启动Agent。

Docker命令在旧Windows终端未进入PATH时，可重新打开终端或执行 `powershell -File .\start_erp.ps1`。ERP网页：http://localhost:8080 ，seed本地账户 Administrator / admin。

## 使用

直接用中文或英文提问，例如：

- What's the current stock of copper coil?
- Show me overdue sales invoices.
- 请按客户汇总未收回发票余额，不要只看逾期。
- Create a new purchase order for 100 m of RM-COIL-CU-2.0 from Tongling Magnet Wire Co. at $29 per meter.

采购工具生成预览，CLI独立打印实际载荷。只有人工输入 `/confirm <proposal-id>` 才创建并回读草稿；模型不具备直接创建、确认或取消工具。只支持单行采购、公司本位币、物料stock_uom；多公司要求明确公司。不自动提交订单。

| 命令 | 用途 |
|---|---|
| /pending | 查看本机保存的采购proposal及状态/是否过期 |
| /confirm id | 确认未过期预览，重新校验后创建草稿 |
| /discard id | 撤销pending预览，不改ERP单据 |
| /reset | 清除模型对话，保留本地采购journal |
| /quit | 退出 |

交互CLI的状态存放 `.local/proposals.sqlite3`，Git与交接ZIP均排除该目录。预览15分钟过期。创建超时、进程中断或回读异常后，保留状态/已知单号以便人工核对，不自动重复POST。金额是行金额估算，税费和默认值差异在回读时显示review_required；单据仍为草稿。

## 验证

```text
python -m unittest discover -s tests -v
python verify_live.py
python verify_llm.py
python verify_extended.py
```

- 29项代码测试覆盖HTTP、确认、重启、并发、异常、完整分页、Decimal计算与对话恢复。
- verify_live.py默认只读，原题真实REST检查19项。
- verify_llm.py真实调用模型，保存十个原题的工具轨迹；答案须人工核对，脚本不把“有回复”当作答对。
- verify_extended.py检查未结应收/应付完整汇总，并真实询问新问题。模型调用可能消耗账户额度。
- 仅对本地seed显式执行 `python verify_extended.py --create-test-po` 会测试一次真实模型预览、持久化、确认与回读；已有audit_write.json收据时拒绝再建。当前已执行，勿再次写入或删除收据来重跑。

先前真实测试草稿00028、本轮审计草稿00029均未提交；采购单总数29。原有已提交开放采购单仍6张、$15,065.50，库存未因草稿变化。不要为重启删除数据库卷。

## 设计与交付状态

七个模型工具：元数据、计数、带完整性标记的分页列表、详情、完整聚合、受限Decimal算术、采购预览。新增只读DocType可复用工具；新增写入需专用验证/确认适配。

完整架构、流程、业务坑和限制见 **ARCHITECTURE.md**；当前审计结论见 **AUDIT.md**；设计取舍见 WRITEUP.md；实测证据在 evidence/。原始ERP文件保持不变。

代码尚未上传GitHub，尚未向招聘方提交链接。后续提交应保留现有多次Git提交，排除.env、.local及其他本机配置。样例与新增问题通过不构成对所有隐藏题的准确率保证。
