# Plantcore ERPNext Agent

通过实时 ERPNext API 回答库存、采购、工单、BOM 和财务问题，并在人工确认后创建采购草稿。使用 Python 标准库 CLI、七个模型工具和本地 SQLite 确认日志；题目提供的 ERPNext 环境保留在 `erpnext/`。

第一次接手请读 [项目指南](PROJECT_GUIDE.md)；原题与评分要求见 [ORIGINAL_README.md](ORIGINAL_README.md)。

## 启动

需要 Python 3.10+、Docker Desktop/Engine 与 Compose，以及可用的模型 API 配置。命令均在项目根目录运行；Linux/macOS 可将 `python` 换成 `python3`。无需安装第三方 Python 运行库。

```text
docker compose -f erpnext/compose.yml up -d
docker compose -f erpnext/compose.yml logs -f restore-site
```

首次等待 `Restore complete.`；已有站点可能跳过恢复。`Ctrl+C` 退出日志查看。首次镜像下载与恢复所需时间取决于网络。

仅在根目录没有 `.env` 时复制样例：

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux/macOS
cp .env.example .env
```

在本机 `.env` 填写 `LLM_API_KEY`，核对 `LLM_BASE_URL`、`LLM_MODEL`；样例提供百炼配置。ERP 配置为 `ERPNEXT_URL`、`ERPNEXT_API_KEY`、`ERPNEXT_API_SECRET`。不覆盖已有配置，不提交密钥。

```text
python agent.py --check
python agent.py
```

`--check`检查 ERP 连接与模型配置是否存在，不调用模型，不能证明模型权限或余额可用。模型 API 在充值后已恢复真实问答；最新状态与逐题记录见 [AUDIT.md](AUDIT.md)。ERP 页面为 [localhost:8080](http://localhost:8080)，本地 seed 登录为 `Administrator` / `admin`。

作业业务参考日保持 **2025-10-15**。机器日期和单号年份不能替代它；写入也显式传入交易日与需求日。

## 使用

可以先问：

```text
铜线的现货、在途和生产预留分别有多少？请列出单位和仓库。
Show me overdue sales invoices.
按供应商和币种汇总已提交采购发票的未付余额。
```

| 命令 | 作用 |
|---|---|
| `/trace` | 查看上一模型轮的实际工具收据、查询范围、分页与错误 |
| `/pending` | 查看本机保存的采购预览及状态 |
| `/confirm id` | 明确确认该预览，重新校验后创建并回读草稿 |
| `/discard id` | 撤销本地待确认预览，不改变 ERP 单据 |
| `/reset`、`/quit` | 清对话、退出；重置对话不删除采购状态 |

采购先显示真实载荷与具体 ID，只有人工 `/confirm id` 才写入。模型不能直接确认、创建、提交或取消。预览默认 15 分钟有效，绑定 ERP 端点与凭据配置；状态保存在被 Git 忽略的 `.local/proposals.sqlite3`。创建超时或回读异常后先对账，不盲目重试。当前支持单行、公司本位币、物料库存单位，税费/默认值差异在回读中标记人工复核。

## 验证与已知边界

本地代码测试和真实 REST 检查：

```text
python -m unittest discover -s tests -v
python verify_live.py
```

54 项代码测试、19 项真实 REST 复核通过；从非项目目录按脚本路径启动 `--check` 也通过。按需运行模型案例会消耗 API 额度，使用新的输出文件保留审计：

```text
python verify_variants.py --output variants_my_run.json
python verify_conversation.py --output conversation_my_run.json
```

充值后完整八题复跑的核心要求 8/8 符合，完整回答为 6 通过、2 部分通过；随后定向修复了歧义采购的查询范围表述，库存题仍有额外公式未调用 `calculate`。三轮“库存→缺口→采购预览”核心和预览断言通过，第二轮附加情景公式仍需改进。细节见 [真实复测人工分级](evidence/FOLLOWUP_REVIEW.md)，历史失败保留在审计中，不宣称所有文字都正确。

`query_scope`、Bin 快照警告和 `/trace`帮助核证；`answer_checks.py`只对已知库存历史措辞做受限检查，不是通用真值验证器。完整聚合不是事务快照；本地 SQLite 防重不是多机器全局幂等。未实现多行/外币采购、自动取消、生产权限隔离与高并发服务。模型答案仍须核对证据。

真实测试草稿及本地记录数量见审计，不是评审者 fresh seed 的启动条件。不要为普通重启删除数据库卷或确认日志。

## 阅读入口

[项目指南](PROJECT_GUIDE.md) · [架构](ARCHITECTURE.md) · [设计与 AI 工作流程](WRITEUP.md) · [技术选型复核](TECH_REVIEW.md) · [审计与交付状态](AUDIT.md) · [交接记录](HANDOFF.md)
