# Frozen paired answers and evidence

First attempts only. Full JSON histories, HTTP events and provider usage are linked below. No additional model calls for review.


## D01 baseline

[Raw answer, history, receipts, HTTP events and usage](evidence/D01_baseline.json).

Model calls: 6; ERP HTTP: 8; ask elapsed: 41.526s.

**RM-COIL-CU-2.0（Copper Coil 2.0mm）— Crestwind Compressor Manufacturing Co.，已提交（docstatus=1）、transaction_date ≤ 2025-10-15 的采购订单行**

| 指标 | 值 |
|---|---|
| 匹配行数 | 4 |
| 不同父单数 | 4 |
| 数量合计 | 900 Meter |
| 行 amount 合计 | 25,540.00 USD |
| rate 最低 / 最高 | 28.00 / 29.00 USD per Meter |
| 按 qty 加权均价 | **28.38 USD/Meter**（分子 25,540.00 USD ÷ 分母 900 Meter = 28.3777…，四舍五入两位） |

**明细行：**
- PUR-ORD-2026-00001（2025-01-08）：qty 300，rate 28.00，amount 8,400.00
- PUR-ORD-2026-00007（2025-03-05）：qty 200，rate 28.20，amount 5,640.00
- PUR-ORD-2026-00012（2025-05-06）：qty 200，rate 28.50，amount 5,700.00
- PUR-ORD-2026-00022（2025-09-10）：qty 200，rate 29.00，amount 5,800.00

**币种与单位：** 全部 4 张订单币种均为 USD（conversion_rate=1.0），行单位均为 Meter（uom=stock_uom，conversion_factor=1.0），未混合币种或单位。四单供应商均为 Tongling Magnet Wire Co.。

**覆盖范围：** 通过子表条件 [Purchase Order Item, item_code = RM-COIL-CU-2.0] 过滤父单，列表返回 total=4、has_more=false，覆盖完整；随后逐一读取全部 4 张父单明细（4/4 成功），每张订单各含 1 行匹配物料。本次为只读查询，未生成任何采购预览。数据获取时间为 2026-10-18 03:04 UTC（实时读取）。


## D01 experiment

[Raw answer, history, receipts, HTTP events and usage](evidence/D01_experiment.json).

Model calls: 4; ERP HTTP: 6; ask elapsed: 47.384s.

**RM-COIL-CU-2.0（Copper Coil 2.0mm）— Crestwind Compressor Manufacturing Co.，已提交（docstatus=1）采购订单，transaction_date ≤ 2025-10-15**

| 指标 | 结果 |
|---|---|
| 匹配明细行数 | 4 行 |
| 不同父单数 | 4 张 |
| 数量合计 | 900 Meter |
| 行 amount 合计 | 25,540.00 USD |
| rate 最低 / 最高 | 28.00 / 29.00 USD每Meter |
| qty 加权 rate 均价 | **28.38 USD/Meter**（分子 25,540.00 USD ÷ 分母 900 Meter = 28.3778 → 四舍五入两位 28.38） |

**明细行（父单 / 交易日 / qty / rate / amount）：**
- PUR-ORD-2026-00001 / 2025-01-08 / 300 / 28.00 / 8,400.00
- PUR-ORD-2026-00007 / 2025-03-05 / 200 / 28.20 / 5,640.00
- PUR-ORD-2026-00012 / 2025-05-06 / 200 / 28.50 / 5,700.00
- PUR-ORD-2026-00022 / 2025-09-10 / 200 / 29.00 / 5,800.00

**币种与单位：** 全部 4 张订单币种均为 USD（conversion_rate=1.0），行 UOM 与 stock_uom 均为 Meter，未混合币种或单位。

**查询覆盖范围：** 过滤条件为 docstatus=1、transaction_date ≤ 2025-10-15、company = Crestwind Compressor Manufacturing Co.、子表 item_code = RM-COIL-CU-2.0；列表返回 total=4、has_more=false（覆盖完整），随后逐张读取全部 4 张父单明细（complete=true）。仅限该精确过滤范围，未包含草稿/取消单据。本次为只读分析，未生成任何采购预览。


## D02 baseline

[Raw answer, history, receipts, HTTP events and usage](evidence/D02_baseline.json).

Model calls: 5; ERP HTTP: 6; ask elapsed: 51.737s.

**FG-COMP-1.5HP-R32｜Crestwind Compressor Manufacturing Co.｜已提交销售订单（docstatus=1），transaction_date ≤ 2025-10-15**

| 指标 | 值 |
|---|---|
| 匹配明细行数 | 5 |
| 不同父单数 | 5（无重复父单） |
| 数量合计 | 60 Nos |
| 行 amount 合计 | 43,225 USD |
| rate 最低 / 最高 | 720 USD / 725 USD |
| 按 qty 加权均价 | **720.42 USD/Nos** |

加权均价计算：分子 = 行 amount 合计 = 7,200 + 8,640 + 5,760 + 18,000 + 3,625 = **43,225 USD**；分母 = qty 合计 = 10 + 12 + 8 + 25 + 5 = **60 Nos**；43,225 ÷ 60 = 720.4166666…，四舍五入两位小数 = **720.42**。

明细证据（父单 / 交易日 / qty / rate / amount，均为 USD、Nos）：
- SAL-ORD-2026-00009｜2025-06-16｜10｜720｜7,200
- SAL-ORD-2026-00010｜2025-06-30｜5｜725｜3,625
- SAL-ORD-2026-00015｜2025-08-29｜12｜720｜8,640
- SAL-ORD-2026-00018｜2025-09-18｜8｜720｜5,760
- SAL-ORD-2026-00020｜2025-09-25｜25｜720｜18,000

币种与单位：全部 5 行 currency = USD，uom = stock_uom = Nos，单一币种单一单位，无混合。

查询覆盖范围：过滤条件为 company = Crestwind Compressor Manufacturing Co.、docstatus = 1、transaction_date ≤ 2025-10-15、子表 Sales Order Item.item_code = FG-COMP-1.5HP-R32。分页返回 returned=5、total=5、has_more=false，即该过滤条件下覆盖完整；草稿/已取消单据及参考日之后的订单不在范围内。本次为只读查询，未生成任何采购预览。


## D02 experiment

[Raw answer, history, receipts, HTTP events and usage](evidence/D02_experiment.json).

Model calls: 6; ERP HTTP: 7; ask elapsed: 49.855s.

**FG-COMP-1.5HP-R32 已提交销售订单明细统计**（Crestwind Compressor Manufacturing Co.，transaction_date ≤ 2025-10-15，docstatus=1）

| 指标 | 结果 |
|---|---|
| 匹配行数 | 5 |
| 不同父单数 | 5 |
| 数量合计 | 60 Nos |
| 行 amount 合计 | 43,225.00 USD |
| rate 最低 | 720.00 USD |
| rate 最高 | 725.00 USD |
| qty 加权 rate 均价 | **720.42 USD/Nos**（分子 Σ(qty×rate)=43,225，分母 Σqty=60；43,225÷60=720.4166…，四舍五入两位小数） |

**匹配明细行**（均为 USD、UOM=Nos）：
- SAL-ORD-2026-00009（2025-06-16）：qty 10，rate 720，amount 7,200
- SAL-ORD-2026-00010（2025-06-30，第2行）：qty 5，rate 725，amount 3,625
- SAL-ORD-2026-00015（2025-08-29）：qty 12，rate 720，amount 8,640
- SAL-ORD-2026-00018（2025-09-18）：qty 8，rate 720，amount 5,760
- SAL-ORD-2026-00020（2025-09-25）：qty 25，rate 720，amount 18,000

**覆盖范围与口径**：查询按公司、docstatus=1、transaction_date ≤ 2025-10-15 及子表 item_code 精确过滤，返回 5 个父单（has_more=false，覆盖完整），并逐一读取全文核对；仅统计 item_code=FG-COMP-1.5HP-R32 的行（SAL-ORD-2026-00010 中另一行 FG-COMP-1HP-R32 已排除）。所有行币种均为 USD、单位均为 Nos，未混合币种或单位。本次为只读分析，未生成任何采购预览。
