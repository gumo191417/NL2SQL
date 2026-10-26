from sqlalchemy import Result, text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self,session: AsyncSession):
        self.session = session

    async def get_column_type_by_table_id(self, table_id:str):
        sql = f"show columns from {table_id}"
        result:Result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_value_by_table_id(self,table_id:str,column_name:str,limit:int = 10) -> list[str]:
        sql = f"select distinct {column_name} from {table_id} limit {limit}"
        result : Result = await self.session.execute(text(sql))
        return result.scalars().fetchall()

    async def get_db_info(self):
        result = await self.session.execute(text("select version()"))
        version = result.scalar()
        dialect = self.session.get_bind().dialect.name
        return {"version": version, "dialect": dialect}

    async def validate_sql(self, sql):
        await self.session.execute(text(f"explain {sql}"))

    async def execute_sql(self, sql):
        result: Result = await self.session.execute(text(sql))
        return [dict(row_mapping) for row_mapping in result.mappings().fetchall()]