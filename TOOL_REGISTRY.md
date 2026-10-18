# 工具注册、增删与运行边界

上一版是`TOOL_DEFS`加`if/elif`分发，新增工具要同时修改元数据和执行分支。本轮将二者合并到注册表：`erp_tools.py`在每个工具函数旁注册Schema，`tool_registry.py`管理发现、启停、移除和执行契约，Runner不再按工具名写执行分支。

## 默认运行时工具

原基线为8个：`get_doctype_meta`、`count_documents`、`list_documents`、`get_document`、`get_documents`、`aggregate_documents`、`calculate`、`prepare_purchase_order`；当前默认分支另增加 `summarize_details`，共9个。新工具仅接受当前轮真实 `get_document`/`get_documents` 返回正文的显式 `evidence_ref`，不允许模型自填数字或跨轮引用。它们是本项目的ERP API/算术适配器，没有接入外部MCP工具服务器或自动下载插件。`confirm/reconcile/discard`是人工CLI操作，不属于模型工具集合。

未见过的只读DocType通常可以直接复用通用工具，无需每个单据新增一个函数。确实出现新的独立能力时再注册新工具。

## 注册表保存什么

| 内容 | 作用 |
|---|---|
| 函数Schema | 工具名、说明、参数与必填项，发送给模型 |
| handler | 统一的同步`handler(context, args)`入口 |
| effect | read或prepare；不接受write等直接写入分类 |
| version | 开发者维护的版本标签，写入工具收据 |
| decimal_arguments | JSON小数字面是否先保留为Decimal；报价沿用该策略 |
| enabled | 当前Runner是否向模型开放该工具 |

Schema注册时复制，调用方修改原字典或发现结果不会改掉已注册契约。重复名称不会静默覆盖。`agent.TOOL_DEFS`仅为旧代码/测试保留的元数据导出；运行时以`runner.registry`为准，不能修改旧常量来管理工具。

注册表统一检查参数对象、必填项、未知参数及顶层基本类型，默认不接受额外参数。它不是完整JSON Schema验证器；嵌套约束及业务合法性仍由handler、查询策略和ERP客户端校验。新增工具必须实现自己的输入/输出和业务检查，不能只写一份Schema就认为执行安全。

当前接受简单顶层类型；union类型等复杂契约需要可信适配，不会假装已经提供全量JSON Schema兼容。

## 当前会话启停

```text
/tools
/tools disable calculate
/tools enable calculate
```

这些命令不请求模型、不修改ERP。停用后后续模型请求不携带该工具；即使模型照着历史工具名发起调用，执行器也会拒绝。每个Runner默认复制内置目录，A会话停用不改变B会话或全局默认。

启停只保存在当前进程，不写入配置文件；重启恢复当前默认9个。`/reset`只清对话，当前进程的工具启停继续保留。同步CLI在问题之间接收命令；它不能在一个阻塞请求中同时接受下一条CLI输入。

## 新增与移除

受信宿主代码可以在进程运行中注册工具，不必修改Runner。以下是一个简化的真实读取示例；默认已有通用count，因此它只用于演示扩展接口：

```python
from agent import Agent, ERPNextClient, LLMRunner

runner = LLMRunner(Agent(ERPNextClient()))
schema = {
    "type": "function",
    "function": {
        "name": "count_items_extension",
        "description": "Count live Item records; no filters or writes.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

def count_items(context, args):
    return {"count": context.agent.c.count("Item")}

runner.registry.register(schema, count_items, effect="read", version="1")
# 下一次模型请求会发现它；也可以停用再启用。
runner.registry.set_enabled("count_items_extension", False)
runner.registry.set_enabled("count_items_extension", True)
runner.registry.unregister("count_items_extension")
```

内置工具采用相同的`@BUILTIN_TOOLS.tool(schema, ...)`注册方式。没有文件目录监视、任意脚本执行或无须重启的Python模块自动重载；新代码要由可信宿主显式接入。工具目前同步顺序执行，注册表并不提供异步调度或自动横向扩容。

## 运行中变更如何保持一致

每次发模型HTTP请求前，取得该次请求的工具视图，参数契约和handler来自同一条注册记录。

- 新注册工具只有进入下一次模型请求的Schema后才能调用；当前旧视图猜出的新名字会被拒绝。
- 停用或移除会阻止后续调用，即使旧视图仍记得该名字。
- 移除后同名重注册，旧视图不能悄悄调用新handler；下一次请求重新发现契约。
- 已经领取并开始执行的handler可以完成，不能靠停用宣称远端请求已取消或副作用回滚。
- 全部停用时省略`tools/tool_choice`，避免向兼容API发送无效空列表。模型应说明缺少能力，不编造实时数据。

收据仍由真实工具消息生成。Runner同时按call_id保留注册记录的version/effect/小数解析策略；新增工具自动获得通用结果收据，无需修改摘要分支。已有ERP工具的专用摘要与库存语义检查继续保留；新业务语义的完整性门禁仍需另行设计，不能由注册表自动推导。

## 安全与伸缩性不混为一谈

模型没有注册、启用、停用或移除工具的管理能力。注册API只面向可信代码，保留confirm/reconcile/通用创建/SQL/Shell等名字，并仅允许read/prepare分类。但effect是开发者声明，注册表无法证明任意Python函数没有副作用，**不是不可信插件沙箱**。正式接入外部工具仍需权限、凭据、网络、超时和审计策略。

启停是模型能力视图，不是数据授权：停用get_document不代表get_documents也不能读相同单据；数据权限仍须ERP账号控制。停用prepare也不会撤销既有预览，取消本地意图应使用discard。人工confirm依旧独立受载荷审阅、目标绑定与持久状态约束。

工具集合可扩展不等于吞吐自动伸缩。工具很多时，应按权限/任务缩小暴露集合，测量上下文和选择质量；当前没有自动工具检索路由、多进程注册中心或跨机器配置同步。

## 验证

注册表阶段128项代码测试通过，新增13项覆盖注册发现、重复拒绝、Schema复制、停用、同名替换、会话隔离、Decimal解析、旧视图拒绝、空工具集合、收据和CLI控制；见`evidence/unit_registry.txt`。API效率阶段当前145项，新增请求预算与新鲜度保护见[API_EFFICIENCY](API_EFFICIENCY.md)。工具数量与实际HTTP请求量需分开统计。

原基线时期，`evidence/registry_live.json`实际临时注册了第9个工具，模型调用它从真实ERP读取Item=18；移除回到8个后旧名字不可调用，停用/恢复calculate得到7→8。该演示没有持久修改默认工具集，没有ERP写入，也不是新的业务质量评分。

原基线默认8工具的真实模型协议再次通过，见`evidence/registry_model_check.json`。原基线8个内置handler的机械提取与原版本AST等价，见`evidence/registry_extraction.json`；新增注册校验和启停行为另由上述测试覆盖。
