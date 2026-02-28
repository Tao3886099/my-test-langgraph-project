from typing import List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from agent.utils.log_utils import log


class MySQLDataBaseManager:
    """MySQL数据库管理器，提供连接和执行SQL语句的功能"""

    def __init__(self, connection: str):
        """初始化数据库管理器

        Args:
            connection: 数据库连接字符串，格式为 "mysql+pymysql://user:password@host:port/database"
        """
        self.connection = connection
        # 这里可以添加实际的数据库连接逻辑，例如使用 SQLAlchemy 创建引擎等
        self.engine = create_engine(connection, pool_recycle=3600, pool_size=5, max_overflow=10)

    def get_table_names(self) -> list[str]:
        """获取数据库中的表名列表"""
        try:
            # 创建一个数据库映射对象获取数据库中的表名
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except SQLAlchemyError as e:
            log.exception(e)
            raise ValueError(f"获取表名时发生错误: {str(e)}")


    def get_table_comments(self) -> List[dict]:
        """
        获取数据库中所有表的名称和注释信息

        Returns:
            List[dict]: 包含表名称和注释信息的字典列表，每个字典包含 'table_name' 和 'comment' 键
        """
        try:
            # 构建查询语句获取表名称和注释信息
            query = text("""
                        SELECT table_name, table_comment
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE()
                            AND table_type = 'BASE TABLE'
                        Order by table_name
            """)

            with self.engine.connect() as connection:
                result = connection.execute(query)
                table_comments = [{ "table_name": row[0],"comment": row[1]} for row in result]
                return table_comments
        except SQLAlchemyError as e:
            log.exception(e)
            raise ValueError(f"获取表注释时发生错误: {str(e)}")

    def get_table_schema(self, table_names: Optional[List[str]] = None) -> str:
        """获取指定表的模式信息（主键，外键，注释信息等）

        Args:
            table_name: 表名，如果为 None 则获取所有表的字段信息

        Returns:
            包含字段信息的字典列表，每个字典包含 'column_name', 'data_type', 'is_nullable' 等键
        """
        try:
            inspector = inspect(self.engine)
            if table_names is None:
                table_names = inspector.get_table_names()

            schema_info = []
            for table_name in table_names:
                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                primary_keys = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)

                # 构建表模式信息
                table_schema = f"表名: {table_name}\n"
                table_schema += "列信息:\n"
                for column in columns:
                    # 检查该列是否在主键约束中
                    pk_indicator = " (主键)" if column['name'] in primary_keys else ""
                    # 获取字段注释，如果不存在则显示‘无注释’
                    column_comment = column.get('comment', '无注释')
                    table_schema += f"  - {column['name']} ({column['type']}){pk_indicator})[注释: {column_comment}]\n"
                if foreign_keys:
                    table_schema += "外键约束:\n"
                    for fk in foreign_keys:
                        table_schema += f"  - 列: {fk['constrained_columns']} -> 参照表: {fk['referred_table']}({fk['referred_columns']})\n"
                if indexes:
                    table_schema += "索引信息:\n"
                    for index in indexes:
                        unique_indicator = " (唯一索引)" if index.get('unique', False) else ""
                        table_schema += f"  - 索引名: {index['name']} 列: {index['column_names']}{unique_indicator}\n"
                schema_info.append(table_schema)
            return "\n".join(schema_info) if schema_info else "未找到表的模式信息。"

        except SQLAlchemyError as e:
            log.exception(e)
            raise ValueError(f"获取表模式信息时发生错误: {str(e)}")



    def execute_query(self, query: str) -> str:
        """执行SQL查询语句并返回结果

        Args:
            query: 要执行的SQL查询语句

        Returns:
            查询结果的字符串表示
        """

        # 安全检查：防止数据修改操作
        forbidden_statements = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE']
        if any(statement in query.upper() for statement in forbidden_statements):
            raise ValueError("出于安全考虑，禁止执行数据修改操作的SQL语句。")
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                rows = result.fetchall()
                # 将结果转换为字符串表示
                result_str = "\n".join([str(row) for row in rows])
                log.info(f"执行查询成功，返回结果是:\n{result_str}")
                return result_str
        except SQLAlchemyError as e:
            log.exception(e)
            raise ValueError(f"执行查询时发生错误: {str(e)}")

    def validate_query(self, query: str) -> bool:
        """验证SQL查询语句的合法性

        Args:
            query: 要验证的SQL查询语句

        Returns:
            如果查询语句合法则返回 True，否则返回 False
        """
        # 基本语法检查
        if not query or not query.strip():
            return False
        # 仅允许 SELECT或 WITH 语句
        if not query.strip().lower().startswith(("select", "with")):
            return False

        #尝试解析查询语句（不实际执行）
        try:
            with self.engine.connect() as connection:
                connection.execute(text(f"EXPLAIN {query}"))
            return True
        except SQLAlchemyError as e:
            log.exception(e)
            return False

if __name__ == "__main__":
    # 示例用法

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
    # table_names = db_manager.get_table_names()
    # print(table_names)
    #
    # table_comments = db_manager.get_table_comments()
    # print(table_comments)

    table_colums = db_manager.get_table_schema(["sys_user","sys_role"])
    print(table_colums)

    # table_query = "SELECT * FROM sys_user LIMIT 5;"
    # query_result = db_manager.execute_query(table_query)
    # print(query_result)
    #
    # valid_query = "SELECT * FROM sys_user;"
    # invalid_query = "DROP TABLE sys_user;"
    # print(db_manager.validate_query(valid_query))  # 应该返回 True
    # print(db_manager.validate_query(invalid_query))  # 应该返回 False
