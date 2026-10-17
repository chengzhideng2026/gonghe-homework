# Plantcore ERPNext Agent

通过实时 ERPNext API 回答库存、采购、工单、BOM 和财务问题，并在人工确认后创建采购草稿。使用 Python 标准库 CLI、八个模型工具和本地 SQLite 确认日志；题目提供的 ERPNext 环境保留在 `erpnext/`。

第一次接手请读 [项目指南](PROJECT_GUIDE.md)；原题与评分要求见 [ORIGINAL_README.md](ORIGINAL_README.md)。

## 启动

需要 Python 3.10+、Docker Desktop/Engine（推荐28+）、Compose2.24.4+，以及可用的模型 API 配置。命令均在项目根目录运行；Linux/macOS 可将 `python` 换成 `python3`。无需安装第三方 Python 运行库。

```text
docker compose -f erpnext/compose.yml -f compose.local.yml up -d
docker compose -f erpnext/compose.yml -f compose.local.yml logs -f restore-site
```

首次等待 `Restore complete.`；已有站点可能跳过恢复。`Ctrl+C` 退出日志查看。首次镜像下载与恢复所需时间取决于网络。

`compose.local.yml`保留原题文件，将ERP仅发布到127.0.0.1与::1；日后启动继续带此overlay，避免回到全网卡发布。当前Nginx入口没有实现多副本负载均衡。HTTP、防注入、权限与生产化取舍见[SECURITY_AND_DEPLOYMENT](SECURITY_AND_DEPLOYMENT.md)。

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

远端API要求HTTPS，本机回环允许HTTP；基础URL不接受内嵌凭据/查询串。API重定向拒绝，响应大小有上限，错误遮蔽当前凭据。当前seed管理员权限较宽，只用于本机作业；正式部署必须配置最小权限账号。

```text
python agent.py --check
python agent.py --check-model
python agent.py
```

`--check`只查 ERP 连接和配置存在，不调用模型。`--check-model`是可选的真实模型/只读工具检查，会消耗 API 额度，失败区分 configuration、erp、model、tool_protocol 阶段；已在本地约 5 秒完成 Item=18 回路。默认启动 CLI 不请求模型，输入问题后才调用。最新状态见 [评分复核](evidence/SCORING_REVIEW.md) 与 [AUDIT](AUDIT.md)。ERP 页面为 [localhost:8080](http://localhost:8080)，本地 seed 登录为 `Administrator` / `admin`。

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
| `/pending` | 查看当前连接保存的采购预览及状态 |
| `/confirm id` | 明确确认该预览，重新校验后创建并回读草稿 |
| `/reconcile id` | 中断创建已有单号时，只读回查原单并更新本地核查结果 |
| `/discard id` | 撤销本地待确认预览，不改变 ERP 单据 |
| `/reset`、`/quit` | 清对话、退出；重置对话不删除采购状态 |

采购先显示真实载荷与具体 ID，只有人工 `/confirm id` 才写入。模型不能直接确认、创建、提交或取消。报价必须明确 `currency`，与公司本位币不符即拒绝，不自动换汇或把外币报价改名为本位币。报价 JSON 小数先保留为 Decimal，再校验数值范围与 ERP 浮点可表示性；收据保留报价小数文本。当前支持单行、物料库存单位，税费/默认值差异在回读中标记复核。

预览默认 15 分钟有效，绑定 ERP 端点与凭据配置；查询和修改均检查绑定，状态在被 Git 忽略的 `.local/proposals.sqlite3`。已知单号可 `/reconcile id`，没有收到单号则人工核查，禁止盲重发。它提供同日志、同预览防重复派发，没有 ERP 服务端全局幂等键，也没有 SaaS 租户鉴权。

纯天气、吃饭问题由同一模型按业务范围规则引导返回；混合问题处理其中的ERP部分。这是软提示路由。恢复、记忆、检索、模型路由与租户的详细取舍见 [RECOVERY_AND_DESIGN](RECOVERY_AND_DESIGN.md)。

## 验证与已知边界

本地代码测试和真实 REST 检查：

```text
python -m unittest discover -s tests -v
python verify_live.py
```

115项代码测试通过；既有19项REST后，真实join计数/金额及外币拒绝也已验证，见 [SCORING_REVIEW.md](evidence/SCORING_REVIEW.md)。非项目目录按脚本路径启动检查通过。

最新115项输出为`evidence/unit_security.txt`，新增重定向、凭据遮蔽、响应限额和查询语法边界测试；真实模型协议与回环端口验证分别见`model_security_check.json`、`security_live.json`。历史104项和82项输出保留；不将本地验证称为生产安全认证。

按需运行模型案例会消耗API额度，使用新的输出文件保留审计：

```text
python verify_variants.py --output variants_my_run.json
python verify_conversation.py --output conversation_my_run.json
```

新独立H01—H10在旧七工具基线下核心10/10、整段7通过3部分；部分涉及FX公式口径、“分文未收”的证据范围和未查公司缩写。随后修复子表join重复父单，真实ERP和J01模型均确认raw2→distinct1、父金额6600仅计一次，J01核心与整段通过。定向修复题不计入独立集通过率；较早记录见 [FOLLOWUP_REVIEW.md](evidence/FOLLOWUP_REVIEW.md)。

第八工具`get_documents`一次读取至多20个指定父单，逐项成功/错误，部分失败时complete=false。B01三单成功/一单404，批量与核心通过；整段仍部分，因为把“不能称四单完整合计”泛化为所有跨单据合计都无效。明确范围的三单小计仍可计算。B01不计独立十题。

`query_scope`、Bin 快照警告和 `/trace`帮助核证；`answer_checks.py`只检查已知库存历史措辞，不是通用真值验证器。显式子表 join 的列表保留原始行和 offset，父单数量/金额应用 count/aggregate 工具；不能把 join 行数当父单数或静默丢子行。完整聚合不是事务快照；本地防重不是全局幂等。未实现多行/外币采购、自动取消、生产权限隔离和高并发服务，额外断言与公式仍须核对。

真实测试草稿及本地记录数量见审计，不是评审者 fresh seed 的启动条件。不要为普通重启删除数据库卷或确认日志。

## 阅读入口

[项目指南](PROJECT_GUIDE.md) · [架构](ARCHITECTURE.md) · [设计与 AI 工作流程](WRITEUP.md) · [技术选型复核](TECH_REVIEW.md) · [审计与交付状态](AUDIT.md) · [交接记录](HANDOFF.md)
