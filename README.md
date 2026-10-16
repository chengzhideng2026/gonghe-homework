# Plantcore ERPNext Agent

Python 标准库 CLI，使用真实 ERPNext REST/RPC 和兼容 OpenAI Chat Completions 的模型工具调用。原题保留于 `ORIGINAL_README.md`；原始 `erpnext/` 配置和 seed 数据保持完整。仓库沿用交接包内的 Git 历史。

## 快速运行（Windows）

要求：Docker Desktop 已启动，Python 3.10+，Git；无需 pip 安装。首次下载镜像和恢复数据库可能超过 5 分钟；镜像已缓存时按以下步骤启动。

```powershell
cd "D:\work\工核homework\erpnext"
docker compose up -d
docker compose logs -f restore-site
# 看到 Restore complete. 后 Ctrl+C 退出日志
cd ..
Copy-Item .env.example .env  # 仅第一次；不要覆盖已有配置
# 在本机编辑 .env，填写 LLM_API_KEY、LLM_MODEL 和服务商 LLM_BASE_URL
python agent.py --check
python agent.py
```

如果旧终端找不到 docker，可以重新打开终端，或在项目根目录执行 `powershell -File .\start_erp.ps1`，脚本会使用 Docker Desktop 的实际安装路径。`start_agent.ps1` 从自身目录加载项目。配置文件总是读取 `agent.py` 旁边的 `.env`，无需把密钥写入命令历史或提交到 Git。

ERPNext 页面：http://localhost:8080 ，本地 seed 账户 `Administrator` / `admin`。`.env.example` 已包含本地 ERPNext API 测试凭据；模型密钥和模型名称必须自行填写。支持 tools/tool_calls 的 OpenAI-compatible `/chat/completions` 服务；当前实现未验证所有服务商。

## 交互

询问 `What's the current stock of copper coil?`，继续询问工单缺料、订单、毛利或逾期发票。所有事实从实时 API 读取，日期口径固定 `2025-10-15`。

采购订单只会生成预览，显示物料、供应商、数量、单价、总额和日期。输入 `/confirm <proposal-id>` 才创建草稿并回读；不会自动提交订单。模型没有直接写入或取消工具。取消工单存在歧义时应请求澄清，不执行取消。`/quit` 退出。

## 验证与证据

```powershell
python -m unittest discover -s tests -v
python verify_live.py
python verify_llm.py
```

- 单元测试覆盖确认状态机、日期、异常恢复、非有限金额、真实 HTTP 路径编码。
- `verify_live.py` 调用真实 ERPNext，检查库存、开放采购订单、客户排名、工单缺料、毛利基础、逾期发票、空数据、元数据和采购预览。默认只读；证据保存到 `evidence/live_read.json`。
- `verify_llm.py` 需要本机模型密钥，会产生模型 API 调用费用；逐条运行原题问答并保存工具轨迹到 `evidence/llm_acceptance.json`。答案正确性需与原题人工核对，脚本不把“有回复”标记为“答对”。它不会确认写入。
- `python verify_live.py --create-test-po` 明确启用本地测试草稿创建，100 Meter × $29，总额 $2,900。只用于本题 seed 环境。创建前保存尝试记录，成功后记录单号；已有 `evidence/test_po_receipt.json` 时拒绝再次创建。异常后先查询核对，避免重复写入。

完整当前验收状态见 `HANDOFF.md`。测试采购草稿会保留在数据库中，开放已提交订单的 seed 数据不受影响。不要为日常重启使用会删除数据库卷的命令。

## 工具与扩展

模型可调用 `get_doctype_meta`、`count_documents`、`list_documents`、`get_document`、`prepare_purchase_order`。列表支持字段、过滤、排序和分页（每页最多 100）；完整统计应继续翻页或核对 count。详情读取包含子表，可跨 DocType 推理。新增只读 DocType 复用这些工具；新增写入类型需另加验证和显式确认路径。
