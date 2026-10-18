# 最后一组：D02接口修复对照

原问题逐字沿用cases.json。各一次，未重跑。旧四次记录不变。


## baseline

[原始完整轨迹和usage](evidence/interface_D02_baseline.json)

**查询范围**：Sales Order（docstatus=1 已提交），company = Crestwind Compressor Manufacturing Co.，transaction_date ≤ 2025-10-15，明细行 item_code = FG-COMP-1.5HP-R32。列表查询返回 total=5、has_more=false，5 个父单全部读取成功，覆盖完整。

**结果（全部为 USD 币种、Nos 单位，未混合）**：

| 指标 | 值 |
|---|---|
| 匹配明细行数 | 5 行 |
| 不同父单数 | 5 个 |
| 数量合计 | 60 Nos |
| 行 amount 合计 | 43,225.00 USD |
| rate 最低 | 720.00 USD |
| rate 最高 | 725.00 USD |
| 按 qty 加权 rate 均价 | **720.42 USD**（分子 43,225.00 USD ÷ 分母 60 Nos = 720.4166…，四舍五入两位） |

**明细行**：
- SAL-ORD-2026-00009（2025-06-16）：qty 10，rate 720，amount 7,200
- SAL-ORD-2026-00010（2025-06-30）：qty 5，rate 725，amount 3,625（该单另一行 FG-COMP-1HP-R32 不计入）
- SAL-ORD-2026-00015（2025-08-29）：qty 12，rate 720，amount 8,640
- SAL-ORD-2026-00018（2025-09-18）：qty 8，rate 720，amount 5,760
- SAL-ORD-2026-00020（2025-09-25）：qty 25，rate 720，amount 18,000

数据为实时读取（fetched_at 2026-10-18T03:31 UTC），只读操作，未生成任何采购预览。

## fixed

[原始完整轨迹和usage](evidence/interface_D02_fixed.json)

**FG-COMP-1.5HP-R32 · Crestwind Compressor Manufacturing Co. · 已提交销售订单（transaction_date ≤ 2025-10-15）**

| 指标 | 值 |
|---|---|
| 匹配明细行数 | 5 |
| 不同父单数 | 5 |
| 数量合计 | 60.0 Nos |
| 行 amount 合计 | 43,225.00 USD |
| rate 最低 / 最高 | 720.00 / 725.00 USD |
| 按 qty 加权均价 | **720.42 USD/Nos**（分子 sum(qty×rate) = 43,225.00，分母 sum(qty) = 60.0，ROUND_HALF_UP 保留2位） |

**匹配父单（均为 USD、docstatus=1）：**
- SAL-ORD-2026-00009（2025-06-16）：qty 10，rate 720.00，amount 7,200.00
- SAL-ORD-2026-00010（2025-06-30）：qty 5，rate 725.00，amount 3,625.00（该单另含1行 FG-COMP-1HP-R32，已排除）
- SAL-ORD-2026-00015（2025-08-29）：qty 12，rate 720.00，amount 8,640.00
- SAL-ORD-2026-00018（2025-09-18）：qty 8，rate 720.00，amount 5,760.00
- SAL-ORD-2026-00020（2025-09-25）：qty 25，rate 720.00，amount 18,000.00

**币种/单位**：全部为单一分组 USD + Nos（uom=stock_uom，conversion_factor=1），无混合币种或单位。

**覆盖范围**：以子表条件 [Sales Order Item.item_code = FG-COMP-1.5HP-R32] + docstatus=1 + transaction_date ≤ 2025-10-15 + company 精确过滤父单列表，返回 5 条、has_more=false（覆盖完整）；随后逐单读取明细并按 item_code 精确匹配统计（检查6行，排除1行非目标物料）。数据为实时读取（fetched_at 2026-10-18T03:31 UTC）。仅只读查询，未生成任何采购预览。
