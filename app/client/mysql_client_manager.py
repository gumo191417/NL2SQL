import asyncio
from typing import Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession

from app.conf.app_config import DBConfig, app_config


class MysqlClientManager:
    def __init__(self,db_config: DBConfig):
        self.db_config = db_config
        self.engine :Union[AsyncEngine,None] = None

    def _get_url(self):
        return (f"mysql+asyncmy://{self.db_config.user}:{self.db_config.password}@{self.db_config.host}:"
                f"{self.db_config.port}/{self.db_config.database}?charset=utf8mb4")

    def init(self):
        self.engine = create_async_engine(
            self._get_url(),
            pool_size =10,
            pool_pre_ping = 10
        )

    async def close(self):
        await self.engine.dispose()





if __name__ == '__main__':
    dw_mysql_client_manager = MysqlClientManager(app_config.db_dw)
    meta_mysql_client_manager = MysqlClientManager(app_config.db_meta)
    dw_mysql_client_manager.init()


    async def test():
        async with AsyncSession(dw_mysql_client_manager.engine) as session:
            # 执行sql查询
            result = await session.execute(text("select * from fact_order limit 10"))
            # 提取查询结果rows对象结构如：[(),(),()]
            rows = result.fetchall()
            # 提取查询结果封装成字典结构如：[{},{},{}]
            # rows = result.mappings().fetchall()
            # 输出返回结果类型
            print(type(rows[0]))
            # 输出首行数据
            print(rows[0])


    asyncio.run(test())



