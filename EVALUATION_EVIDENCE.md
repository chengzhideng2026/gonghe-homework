# 评测证据与结果索引

**先看结论：项目已建立代码回归、真实 ERP REST 和多轮真实模型业务测试；历史实测覆盖广，但不同提交、不同题集的成绩不合并。最新 60 题统一评测仍处规划阶段。**

## 1. 当前可以核对的数字

| 层级 | 结果 | 代码版本与证明范围 |
|---|---|---|
| **正式版离线回归** | **190 / 190 PASS** | `main-v2`，已合并 [PR #2](https://github.com/chengzhideng2026/gonghe-homework/pull/2)，[GitHub Actions](https://github.com/chengzhideng2026/gonghe-homework/actions) |
| **定向修复候选离线回归** | **227 / 227 PASS** | `59339c7d850cfccd0b144fda694b94fac246ecc8`，[PR #4](https://github.com/chengzhideng2026/gonghe-homework/pull/4)；**尚未合入**；该新 SHA 尚未进行真实模型复测 |
| **已完成的定向真实模型试验** | **6 题：核心 5 PASS / 1 PARTIAL，完整 3 PASS / 1 PARTIAL / 2 FAIL** | **旧候选** `571f52e`，26 次模型请求、24 次 ERP GET、0 写入。FNL-12 通过，付款核销与 EUR 报价仍有缺陷；见 [脱敏报告](evidence/TARGETED_REAL_MODEL_REVIEW_20261018.md)。不能直接算作最新 `59339c7d` 的成绩 |
| **真实 ERP REST 兼容性** | 历史阶段多次 **19 项检查通过** | [只读 REST 原始记录](evidence/live_read.json)；验证数据/接口，不计入模型回答通过率 |
| **FNL 独立业务基线** | 测试线程报告 **12 题、核心 10/12、完整 9/12** | 基线 `2d6ce5c`；原始测试文件目前保存在独立本地工作区，**尚未提交到公开仓库** |
| **统一业务评测** | **60 道计划题，尚无总成绩** | 初步去重后 40 道历史候选题 + 20 道新泛化题；Oracle 尚未冻结、模型尚未执行 |

**阅读规则：**代码测试的数量不等于业务题数量；候选 CI 通过也不等于它已经提升了真实业务回答准确率。最终结论必须带提交 SHA、题数分母、首次运行轨迹。

## 2. 公开可追踪的历史真实模型评测

| 测试系列 | 历史结果：核心 / 完整回答 | 原始证据 |
|---|---|---|
| E01–E08：库存、BOM、账期、歧义与采购 | **8/8、6/8** | [复盘](evidence/FOLLOWUP_REVIEW.md) · [原始结果](evidence/variants_followup.json) |
| H01–H10：业务边界与关联推理 | **10/10、7/10** | [复盘](evidence/SCORING_REVIEW.md) · [原始结果](evidence/scoring_baseline.json)；**较早七工具版本** |
| C01–C06：未知类型、批量、子表、跨轮 | **6/6、4/6**（纠正原错误测试前提后） | [逐题复核](evidence/closeout_review.json)；原 C02 和修正 C02 是同一场景，不能计两题 |
| S01–S03：领域内/外、混合问题 | **3/3、2/3** | [原始结果](evidence/scope_acceptance.json)；是定向行为测试，不是通用分类器准确率 |
| J01 / B01：父子行去重、部分批量成功 | **核心均通过，完整一通过一部分** | [关联 REST](evidence/join_and_currency_live.json) · [批量真实轨迹](evidence/batch_acceptance.json) |
| R01–R03：否定范围、日期、预览措辞 | **保留部分和失败，无统一通过率** | [边界复盘](evidence/ANSWER_BOUNDARIES_REVIEW.md) · [原始结果](evidence/answer_boundaries_after.json) |
| N05 / N07：错误小计、长子表统计 | **定向修复后核心通过** | [首次失败与复测](evidence/N05_N07_REVIEW.md) · [结构化证据](evidence/n05_n07_review.json) |

其他真实日期评测、三轮对话及动态工具扩展见 [AUDIT](AUDIT.md)。这些不是同一个 SHA 的无重叠统一测试集，不将各阶段最优成绩加总。

## 3. 60 题统一评测怎样形成

独立规划收集**原题10、E8、H10、C6、FNL12**，共 46 条候选问题；合并六条实质重复（例如同一 BOM 展开或同一工单缺料），保留 **40 条历史候选问题**；另拟 **20 条泛化问题**，目标60题。新增维度包括 AR 账龄、现金流、利润与估值口径、供应商收货、类别完整性、跨单据关联、双口径补货和采购方案变更。

**规划不是成绩。** 20 道新题的真值还需独立 ERP GET 核验，完整 Oracle/答案不在评测前公开，模型只接收问题。曾有开发修复阶段打开 FNL Oracle 的事实，故那次修复复测不能声称严格盲测；新未见案例应单独标记。

初步估计 60 题需 **240–360 次模型请求、400–700 次 ERP GET**，另有 Oracle 读取。旧评测器 **80 次模型、240 次 ERP GET、1800 秒、20 美元**的每批上限不够一次完整执行。账户持有人已确认服务商额度充足；仍应在正式统一评测前明确批次预算、总成本及失败中止规则；失败、异常、中断、未执行均原样报告，不通过重复采样挑最好结果。

## 4. 最终发布门槛

1. 在 **最新候选 SHA** `59339c7d` 上复核 FNL-07、H08、FNL-02、FNL-12、E07/E08；不得仅凭 227 项 CI 就合并代码。
2. 冻结评测题、Oracle、判分标准和 SHA256；记录模型/参数、ERP seed 与参考日。
3. 对最终候选的每题保留首次回答、工具收据、HTTP 方法、真实 usage 和人工/AI 审核说明；核心、完整、PARTIAL、FAIL、未运行分别计数。
4. 发布首页成绩摘要及可核查的**脱敏**原始证据。历史结果只用于证明修复过程，不能冒充同 SHA 的最终 60 题成绩。

进一步设计说明见 [README](README.md)、[WRITEUP](WRITEUP.md)、[业务验收规则](BUSINESS_ACCEPTANCE.md)。
