"""LangGraph 单节点图模板。

返回一个预设响应。可按需替换逻辑与配置。
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime
from typing_extensions import TypedDict
from agent.utils.log_utils import log

from agent.my_llm import llm
from agent.tools.test_to_sql_tools import (
    ListTablesTool,
    SQLQueryTool,
    SQLQueryValidationTool,
    TableSchemaTool,
)
from agent.utils.db_utils import MySQLDataBaseManager
from agent.env_utils import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def _get_db_config() -> Dict[str, str] | None:
    values = {
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_NAME": DB_NAME,
    }
    if any(not value for value in values.values()):
        return None
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
    }


DB_CONFIG = _get_db_config()
connection = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4"
    if DB_CONFIG
    else None
)


class Context(TypedDict):
    """智能体上下文参数。

    在创建 assistant 或调用图时设置。
    参考: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    my_configurable_param: str


class State(MessagesState):
    """消息状态。"""


SYSTEM_PROMPT = (
    "你是一个多功能智能助手，可以帮助用户完成多种任务。\n\n"
    "===== 能力 1：数据库查询 =====\n"
    "你可以访问数据库来回答用户问题。\n"
    "相关工具：\n"
    "  - sql_db_list_tables —— 列出数据库中所有表及描述信息\n"
    "  - sql_db_table_schema —— 获取指定表的模式信息（字段、类型、主键等）\n"
    "  - sql_db_query —— 执行 SQL SELECT 查询并返回结果\n"
    "  - sql_db_query_validation —— 验证 SQL 查询的正确性与安全性\n"
    "规则：\n"
    "  - 当用户询问任何与数据库相关的问题时，你必须调用相应的工具来获取真实数据，禁止凭空猜测或编造答案。\n"
    "  - 只允许使用 SELECT 或 WITH 查询，禁止任何写操作（INSERT/UPDATE/DELETE/ALTER/DROP/CREATE）。\n"
    "  - 如果用户的问题涉及多个表，你应该先用 sql_db_list_tables 工具查看有哪些表，然后用 sql_db_table_schema 工具了解相关表的结构，最后构造正确的 SQL 查询来获取数据。\n"
    "  - 如果需要查询数据，先用 sql_db_query_validation 验证 SQL，再用 sql_db_query 执行。\n"
    "  - 注意！系统表的前缀不是常用的sys，而是zapx_sys_，例如用户表是zapx_sys_user;业务表的前缀通常是gils，例如国家（地区）信息表是gils_bas_country。\n\n"
    "  - 订单表的前缀是gils_order，例如发货订单主表是gils_order_outdepot，通常他们的子表名是gils_order_outdepot_XXX。\n"
    "  - 返回的结果应该是名称而不是ID，除非用户明确要求返回ID。你应该尽可能提供有用的上下文信息来支持你的答案，例如相关的表名、列名和查询结果中的关键数据点。\n"
    "  - 查询用户信息的时候使用用户昵称(nick_name)来作为查询条件，而不是使用用户账号(user_name)。\n"
    "  - 返回用户信息时，必须包含用户昵称(nick_name)，但不能包含用户账号(user_name)等敏感信息。\n\n"
    "  - 查询失败时，应该先检查 SQL 语法是否正确，表名和列名是否存在，以及查询条件是否合理。你可以使用 sql_db_query_validation 工具来帮助验证 SQL 查询的正确性和安全性。如果验证失败，你应该根据工具返回的错误信息调整 SQL 查询，而不是直接放弃或返回错误给用户。\n\n"
    "===== 通用规则 =====\n"
    "- 根据用户意图自动判断应该使用哪类工具，不要混淆不同能力的工具。\n"
    "- 如果用户的问题不涉及以上任何能力，直接用你的知识回答即可。\n"
    "- 始终用中文回复用户。\n"
)


async def call_model(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """调用 LLM，根据需要触发工具。"""
    messages = list(state["messages"])
    config_value = (runtime.context or {}).get("my_configurable_param")
    system_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    if config_value:
        # 将配置写入系统消息，方便模型理解
        system_messages.append(SystemMessage(content=f"config: {config_value}"))

    messages = system_messages + messages

    log.info(f"调用模型，输入消息是: {messages}")

    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


def get_sql_tools(connection: str) -> List[BaseTool]:
    """获取数据库相关工具。"""
    manager = MySQLDataBaseManager(connection)
    return [
        ListTablesTool(db_manager=manager),
        TableSchemaTool(db_manager=manager),
        SQLQueryTool(db_manager=manager),
        SQLQueryValidationTool(db_manager=manager),
    ]


def get_all_tools() -> List[BaseTool]:
    """汇总所有工具。新增能力时在此处注册即可。"""
    all_tools: List[BaseTool] = []

    # —— 数据库查询工具 ——
    if connection:
        all_tools.extend(get_sql_tools(connection))

    # —— 在此处继续添加其他能力的工具 ——
    # all_tools.extend(get_xxx_tools())

    return all_tools


tools = get_all_tools()

llm_with_tools = llm.bind_tools(tools)

# 定义图
graph = (
    StateGraph(State, context_schema=Context)
    .add_node("assistant", call_model) # 智能体节点，调用 LLM 生成响应
    .add_node("tools", ToolNode(tools)) # 工具节点，根据条件调用工具
    .add_edge("__start__", "assistant") # 从开始节点进入智能体节点
    .add_conditional_edges("assistant", tools_condition, {"tools": "tools", "__end__": END}) # 根据条件从智能体节点进入工具节点或结束
    .add_edge("tools", "assistant") # 从工具节点返回智能体节点继续对话
    .compile(name="New Graph") # 编译图，生成可执行对象
)

