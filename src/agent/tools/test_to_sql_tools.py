from typing import Optional, List
import asyncio

from langchain_core.tools import BaseTool
from pydantic import Field, create_model

from agent.utils.db_utils import MySQLDataBaseManager
from agent.utils.log_utils import log


class ListTablesTool(BaseTool):
    """列出数据库中的所有表以及其描述信息"""

    name: str = "sql_db_list_tables"
    description: str = "列出数据库中的所有表以及其描述信息。当需要了解数据库结构时，可以使用这个工具来获取数据库中有哪些表，以及每个表的描述信息。"

    # 数据库管理器实例
    db_manager: MySQLDataBaseManager

    def _run(self) -> str:
        try:
            table_comments = self.db_manager.get_table_comments()

            result = f"数据库中共有 {len(table_comments)} 张表：\n"
            for i,table in enumerate(table_comments):
                result += f"{i+1}. 表名: {table['table_name']}\n    描述: {table['comment']}\n\n"

            return result
        except Exception as e:
            log.exception(e)
            return f"获取表信息时出错: {str(e)}"

    async def _arun(self) -> str:
        """"异步执行"""
        return await asyncio.to_thread(self._run)


class TableSchemaTool(BaseTool):
    """获取表的模式信息"""

    name: str = "sql_db_table_schema"
    description: str = "获取MySQL数据库中指定表的模式信息，包括主键、外键、字段类型和注释等。输入应是表名列表，例如：['sys_user', 'sys_role']。当需要了解某个表的结构和字段信息时，可以使用这个工具来获取该表的模式信息。"

    # 数据库管理器实例
    db_manager: MySQLDataBaseManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.args_schema = create_model("TableSchemaArgs", table_names=(Optional[List[str]], Field(..., description="要获取模式信息的表名列表，如果为None或空列表，则获取所有表的模式信息。")))

    def _run(self, table_names: Optional[List[str]] = None) -> str:
        try:
            schema_info = self.db_manager.get_table_schema(table_names)
            return schema_info
        except Exception as e:
            log.exception(e)
            return f"获取表模式信息时出错: {str(e)}"

    async def _arun(self, table_names: Optional[List[str]] = None) -> str:
        """"异步执行"""
        return await asyncio.to_thread(self._run, table_names)


class SQLQueryTool(BaseTool):
    """执行SQL查询语句的工具"""

    name: str = "sql_db_query"
    description: str = "执行SQL查询语句的工具。输入应包含要执行的SQL查询语句，例如：SELECT * FROM sys_user;输入应为有效的SQL SELECT查询语句，当需要从数据库中获取特定数据时，可以使用这个工具来执行SQL查询语句并返回结果。"

    # 数据库管理器实例
    db_manager: MySQLDataBaseManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.args_schema = create_model("SQLQueryArgs", query=(str, Field(..., description="要执行的有效的SQL SELECT查询语句。")))

    def _run(self, query: str) -> str:
        try:
            result = self.db_manager.execute_query(query)
            return result
        except Exception as e:
            log.exception(e)
            return f"执行SQL查询时出错: {str(e)}"

    async def _arun(self, query: str) -> str:
        """"异步执行"""
        return await asyncio.to_thread(self._run, query)


class SQLQueryValidationTool(BaseTool):
    """SQL查询语句验证工具"""

    name: str = "sql_db_query_validation"
    description: str = "SQL查询语句验证工具。输入应包含要验证的SQL查询语句，例如：SELECT * FROM sys_user; 当需要验证SQL查询语句的正确性和安全性时，可以使用这个工具来检查SQL查询语句是否存在语法错误或潜在的安全风险。"

    # 数据库管理器实例
    db_manager: MySQLDataBaseManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.args_schema = create_model("SQLQueryValidationArgs", query=(str, Field(..., description="要验证的SQL查询语句。")))

    def _run(self, query: str) -> bool:
        try:
            validation_result = self.db_manager.validate_query(query)
            return validation_result
        except Exception as e:
            log.exception(e)
            return False

    async def _arun(self, query: str) -> bool:
        """"异步执行"""
        return await asyncio.to_thread(self._run, query)


if __name__ == "__main__":
    # 配置数据库连接信息
    DB_CONFIG = {
        "host": "139.159.228.234",
        "port": 3306,
        "user": "root",
        "password": "Tao3886099",
        "database": "ry-vue"
    }
    connection = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4"
    db_manager = MySQLDataBaseManager(connection)

    # tool = ListTablesTool(db_manager=db_manager)
    # print(tool.invoke({}))

    # tool1 = TableSchemaTool(db_manager=db_manager)
    # print(tool1.invoke({"table_names": ["sys_user", "sys_role"]}))

    # table_query = "SELECT * FROM sys_user LIMIT 5;"
    # tool2 = SQLQueryTool(db_manager = db_manager)
    # print(tool2.invoke(table_query))

    valid_query = "SELECT count(*) FROM sys_user;"
    invalid_query = "DROP TABLE sys_user;"
    tool3 = SQLQueryValidationTool(db_manager = db_manager)
    print(tool3.invoke(valid_query))  # 应该返回 True
    print(tool3.invoke(invalid_query))  # 应该返回 False