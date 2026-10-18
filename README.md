# Plantcore ERPNext Agent

## 项目能力

通过实时 ERPNext API 回答库存、采购、工单、BOM 和财务问题，并在人工确认后创建采购草稿。Python 标准库 CLI 默认提供九个模型工具：元数据、计数、列表、单单详情、批量详情、完整聚合、Decimal 算术、证据绑定的明细统计及采购预览。工具收据、上下文预算和执行轨迹帮助追溯查询与计算来源。

**原始已交付应用验收基线为 `5fe679ea3aaffd53042518238acf09866e56bc4b`（`5fe679e`）。本增强版在该应用基础上加入了只读统计工具和对应测试，属于后续代码变更，原始验收结果不能自动视为增强版测试结果。** 公开仓库默认分支为 [main-v2](https://github.com/chengzhideng2026/gonghe-homework/tree/main-v2)。

## 环境要求和启动步骤

需要 Git、Python 3.10+、已运行的 Docker Desktop/Engine（推荐 28+）、Compose 2.24.4+，以及可用的模型 API 配置。无需第三方 Python 运行库。以下命令在项目根目录执行；Linux/macOS 可用 `python3` 替换 `python`。

1. 克隆并进入项目：

   ```text
   git clone --branch main-v2 https://github.com/chengzhideng2026/gonghe-homework.git
   cd gonghe-homework
   ```

2. 启动题目提供的 ERPNext，并等待首次恢复完成：

   ```text
   docker compose -f erpnext/compose.yml -f compose.local.yml up -d
   docker compose -f erpnext/compose.yml -f compose.local.yml logs -f restore-site
   ```

   看到 `Restore complete.` 后按 `Ctrl+C` 退出日志查看；已有站点可能跳过恢复。首次下载镜像和恢复时间取决于网络。以后启动仍须带 `compose.local.yml`，将端口仅发布到 `127.0.0.1` 和 `::1`。浏览器打开 [本地 ERPNext](http://localhost:8080)，题目 seed 登录为 `Administrator` / `admin`。不要为普通重启删除数据卷或确认日志。

3. **仅在项目根目录没有 `.env` 时**复制配置样例，保留已有配置：

   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env
   ```

   ```bash
   # Linux/macOS
   cp .env.example .env
   ```

   在本机 `.env` 填写 `LLM_API_KEY`，核对 `LLM_BASE_URL`、`LLM_MODEL`；样例使用百炼兼容接口。ERP 配置为 `ERPNEXT_URL`、`ERPNEXT_API_KEY`、`ERPNEXT_API_SECRET`，题目 seed 已预置样例密钥对。真实密钥不要提交 Git。远端 API 要求 HTTPS，本机回环允许 HTTP；API 重定向拒绝。

4. 检查并启动：

   ```text
   python agent.py --demo
   python agent.py --check
   python agent.py
   ```

   `--demo` 为本地加载检查；`--check` 检查 ERP 连接和模型配置字段，不调用模型，不能证明模型额度或业务回答正确。默认 CLI 只在输入问题后调用模型。

   **可选**：`python agent.py --check-model` 会调用真实模型及只读工具、消耗 API 额度；只验证连通性与工具协议，不是完整业务验收。

作业业务参考日固定为 **2025-10-15**；机器日期、单号年份不能替代它。发票日期关系以程序参考日证据为准，原始 ERP `status` 单独保留；写入需明确交易日和需求日。

## 三个简短演示

在 `python agent.py` 中依次尝试；输出以当前 ERP 实际数据和工具证据为准。

1. **库存与跨轮计算**：问“铜线的现货、在途和生产预留分别有多少？请列出物料、仓库和单位。”再问“以刚才同一物料和仓库的现货为基础，目标为 180 Nos，缺口是多少？请调用计算工具。”有歧义先确认物料和范围，不能把在途等同现货。
2. **参考日期查询**：问“以 2025-10-15 为参考日，列出已提交的逾期销售发票，显示公司、币种、到期日和未付余额。”输入 `/trace` 查看查询范围、日期证据与计算来源。
3. **采购预览**：提供明确的物料、供应商、公司、数量、库存单位、单价/币种、交易日和需求日，要求“先生成单行采购预览，不确认写入”。用 `/pending` 查看状态；只有人工输入 `/confirm <proposal_id>` 才复验、创建并回读 ERP 草稿。若仅演示预览，用 `/discard <proposal_id>` 撤销本地预览，`/quit` 退出。预览不是已创建订单，模型不能代替确认。

预览默认 15 分钟有效并绑定连接配置，状态保存在被忽略的 `.local/proposals.sqlite3`。失败且已有单号时用 `/reconcile <proposal_id>` 只读核查；未收到单号需人工核查，禁止盲目重发。

## 验收摘要

| 范围 | 已有结论及证据边界 |
|---|---|
| 应用基线 `5fe679e` 的全新克隆 | 170 项测试、248 项子测试通过，`--demo` 成功；属于本地代码验证。开发回归原输出见 [unit_n05_n07_final.txt](evidence/unit_n05_n07_final.txt)。 |
| 开发线程 N05/N07 复测 | 最终两题业务结果通过；开发过程保留首次不足及两次复测，N07 最终仍有一次错误子表请求。见 [开发复测记录](evidence/N05_N07_REVIEW.md)，不代替独立结论。 |
| 独立线程在新 SHA 的首次复测 | N05/N07 均通过；N07 为 17 次 GET、无错误查询。本轮未触发真实错误恢复，其余 8 题未在新 SHA 重跑，不能合并成新版 10/10。独立报告文件已核实存在，位置说明见下文。 |
| 用户本人操作 | 已完成库存、跨轮计算、日期查询及采购预览；未据此认定用户验证了确认写入或全部案例。 |

独立报告为单独保存的 `D:\work\gonghe-eval-runs\5fe679e_20261018\REPORT.md`，已读取核实，**尚未纳入本仓库**，这里不提供不存在的仓库链接。其余历史阶段和失败回答保留在 [AUDIT](AUDIT.md)、[业务验收说明](BUSINESS_ACCEPTANCE.md) 及其证据入口中，阶段结论不自动迁移到新版本。

本地回归可运行 `python -m unittest discover -s tests -v`；有 pytest 环境也可运行 `python -m pytest -q tests`。这些测试不能替代独立真实业务评测。

## 明细统计工具（增强版）

新增只读 `summarize_details`：先使用 `get_document` / `get_documents` 获取父单，复制成功读取结果正文的 `evidence_ref`，然后指定子表字段（例如 `items`）和需要的精确行筛选（例如 `{"item_code":"..."}`）。工具在本地利用 Decimal 计算匹配行数、不同父单数、数量合计、行金额合计、单价极值和按数量加权单价，不发起新的 ERP 请求。统计结果按公司、币种和单位分组，不进行自动换算。

**证据限制**：同一父单重复读取的子表快照必须一致，行顺序不同不算冲突；发现行增删、字段变化或同一快照重复子行身份会拒绝汇总，不拼接跨时刻结果。即使返回 `complete=true`，也只表示引用的父单读取成功；上游父单列表过滤、分页是否完整仍需独立确认。顺序读取并不等于 ERP 事务快照。

历史实验记录保留在 [实验分支](https://github.com/chengzhideng2026/gonghe-homework/tree/experiment/detail-statistics/experiment)；初次比较存在来源引用失败，修复后 D02 只有一组真实成功案例，不能宣称统计工具稳定降低 token、延迟或 HTTP 次数。最终验证以本分支上的实际完整离线回归为准，不把旧版测试记录当成新提交的验收结果。

## 主要限制

- **F01/F02 未覆盖，不能宣称所有隐藏题通过。** 独立 N05/N07 通过不构成长对话稳定性、故障恢复或真实确认写入全覆盖。
- 有限格式的小计检查和已知措辞检查不是通用事实证明器；模型仍可能额外断言，需核对范围、单位、币种和证据。完整聚合不是事务快照，缓存附读取时间而非实时保证。
- 当前轮上下文可能临时超预算；按完整轮裁剪历史不是严格 token 上限，也没有持久聊天检查点。独立 N07 的 `over_budget=true` 已在外部报告记录。
- 采购只支持单行、库存单位及公司本位币；不自动换汇、提交或取消订单。本地原子领取与幂等键不等于 ERPNext 服务端 exactly-once。
- seed 管理员凭据只用于本机作业；尚无生产租户隔离、最小权限服务、负载均衡或高并发保证。真实测试草稿数量不是新 seed 启动条件。

## 深入阅读

- [原题及六项要求](ORIGINAL_README.md) · [一页设计说明](WRITEUP.md) · [项目指南](PROJECT_GUIDE.md) · [交接入口](HANDOFF.md)
- [架构](ARCHITECTURE.md) · [工具扩展](TOOL_REGISTRY.md) · [API 效率](API_EFFICIENCY.md) · [恢复与取舍](RECOVERY_AND_DESIGN.md)
- [安全与部署](SECURITY_AND_DEPLOYMENT.md) · [业务验收标准](BUSINESS_ACCEPTANCE.md) · [审计和历史原始记录](AUDIT.md)
- [开发 N05/N07 记录](evidence/N05_N07_REVIEW.md) · [日期复测](evidence/INVOICE_DATE_REVIEW.md) · [旧版独立题分级](evidence/SCORING_REVIEW.md)
