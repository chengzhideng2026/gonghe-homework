# 发票参考日期判断修复

基线为`ce95390`。旧`answer_boundaries_after.json`中R1把2025-10-18误说成早于2025-10-15的失败原文保留；没有改写历史答案或时间。

## 实际改动

`invoice_due_evidence()`用`date.fromisoformat`比较完整日历日期，以`Decimal`判断当前未结余额是否为正。原有`overdue()`复用同一函数；规则仍为`due_date < reference_date AND outstanding_amount > 0`，到期当天不算逾期。缺失/无效输入为未知，不以零或ERP状态替代。

现有三个读取工具增加`assess_due_date`布尔选项，默认false。问逾期时显式启用，真实`ask()`在工具消息的`data`旁附`reference_date_evidence`，包括参考日、before/on/after、带符号日差和逾期判断。负日差表示到期日在参考日前，正数表示之后。原始`status`、日期和余额字段不改，完整工具消息、收据及历史摘要保留逐单计算证据；本地持久轨迹保留评估头部，逐单嵌套字段仍受原有深度截断限制，完整结果以原始模型报告为准。仍为八个工具；只使用已读取字段，不增加ERP请求，也不增加关键词路由或事实证明器。

余额问题默认不附日期评估，要求原文照录状态，明确`outstanding_amount`是未收余额，不主动解释日期或把余额改述成金额差额。没有改采购预览。

## 程序检查

- 最终163项本地测试通过：`unit_invoice_dates_scoped.txt`。新增5项覆盖参考日前/当天/之后、其他参考日、零/负/极小正余额、无效输入、默认不评估，以及真实`ask()`的单条/列表/部分批量读取。
- `ask()`协议测试确认源记录未变、失败批量成员不冒充成功、日期证据可进收据和历史摘要、不开启时不附加计算，以及没有额外HTTP。模拟模型正文不算业务验收。
- 既有19项REST在初版日期函数上全部通过，见`invoice_dates_rest.json`；后续增补日差和显式开关后，完整本地回归通过，并做最终只读核对`invoice_dates_readback.json`：2次HTTP，已提交未结7条覆盖完整，4条参考日前逾期，计算合计USD25,380。
- 最终核对00018：原始status=`Overdue`，due_date=`2025-10-18`，reference_date=`2025-10-15`，日差`+3`，`overdue_by_reference_date=false`，当前未收余额仍为USD5,760。

参考日用于日期关系；所用余额仍是返回的当前余额，不是历史总账时点回放。docstatus/公司/币种口径另行核验。

## 真实模型与AI复核

本轮共8个用户问答轮：首轮3题、日差/输出指令调整后3题、显式评估开关后仅复跑原R1及原题逾期查询2题。三个原始文件均保留：`invoice_dates_model.json`、`invoice_dates_model_final.json`、`invoice_dates_model_scoped.json`。文件名带final的是中间版本，最新代码对应scoped文件；前两个版本的运行时代码差异保存在initial/refined_code.patch。每次均无ERP POST，采购单名集合29→29。

| 最终题目 | 本轮日期/余额目标 | 完整回答 | 实际证据和限制 |
|---|---|---|---|
| 原R1当前余额 | 通过 | 部分 | 明确未结USD5,760、总额USD5,760、原始Overdue；1次HTTP，未请求日期评估，正文没有主动解释日期，没有“没有净未结差额”。但仍多写假设性收款后退款/取消分配例子，不算完整精简通过。 |
| 原题Show me overdue sales invoices. | 通过 | 部分 | 显式启用程序评估，读回7条未结发票，按参考日列00011/13/15/17，金额6000/4640/8640/6100，calculate得25380，正文一致。2次HTTP，保留原始status，未到期三条没有被算成逾期。公司范围未在正文明确，查询也未投影公司，因此按完整报告标准保留部分。 |

独立的00018日期问题在前两轮均正确回答“参考日未逾期”，原始Overdue分开列出。首轮提到“晚3天”时还没有日差输出，已保留该证据缺口；随后程序补日差，第二轮有`+3`来源。最终显式开关后的该单条路径由`ask()`模拟协议验证，没有另跑第9个真实模型问题。

复核主体是当前Codex主Agent，逐项读正文、工具参数、返回、收据和算术结果；没有另一个模型自评分或正则通用证明。日期错误在本组不再出现，不代表所有额外表述问题已经解决，也不代表留出题通过率。

## 本人操作验证及记录

本人操作验证**尚未执行**。程序通过、AI对照证据和用户亲自操作分别记录于`invoice_dates_review.json`。原R1失败和更早付款/预留失败文件与`ce95390`内容一致；没有修改`.env`、数据卷，未确认/创建/提交/取消/删除ERP单据。

复跑当前定向题可运行（消耗模型额度，必须使用新输出名）：

```text
python verify_answer_boundaries.py --cases invoice_date_final_cases.json --phase after --output my_invoice_dates_run.json
```
