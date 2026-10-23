import asyncio
from argparse import ArgumentParser
from pathlib import Path

from app.client import qdrant_client_manager
from app.client.embedding_client_manager import EmbeddedClientManager
from app.client.es_client_manager import ESClientManager
from app.client.mysql_client_manager import MysqlClientManager
from app.client.qdrant_client_manager import QdrantClientManager
from app.conf.app_config import app_config
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build(config:Path):
    """
    构建元知识库函数
    用于执行构建元知识相关的业务逻辑，例如加载配置、初始化数据等
    """
    dw_mysql_client_manager = MysqlClientManager(app_config.db_dw)
    meta_mysql_client_manager = MysqlClientManager(app_config.db_meta)
    qdrant_client_manager = QdrantClientManager(app_config.qdrant)
    embedding_client_manager = EmbeddedClientManager(app_config.embedding)
    es_client_manager = ESClientManager(app_config.es)

    dw_mysql_client_manager.init()
    meta_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()

    es_client_manager.init()

    async with(dw_mysql_client_manager.session_factory() as dw_session,
               meta_mysql_client_manager.session_factory() as meta_session):
        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository=MetaMySQLRepository(meta_session),
            dw_mysql_repository=DWMySQLRepository(dw_session),
            column_qdrant_repository=ColumnQdrantRepository(qdrant_client_manager.client),
            embedding_client=embedding_client_manager.client,
            value_es_repository=ValueESRepository(es_client_manager.client),
            metric_qdrant_repository=MetricQdrantRepository(qdrant_client_manager.client)
        )

        # 调用业务对象 build 函数 完成元数据知识库的构建
        await meta_knowledge_service.build(config)

        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await qdrant_client_manager.close()
        await es_client_manager.close()

    # 打印INFO级别的日志，记录当前正在执行的操作
    logger.info("Building meta knowledge...")
    logger.info(str(config))


# 判断当前脚本是否作为主程序运行
if __name__ == '__main__':
    # 调用build函数，执行元知识构建逻辑
    parser = ArgumentParser(
        prog='python -m app.scripts.build_meta_knowledge',
        description='通过脚本+额外脚本(-c 传递)参数实现',
        epilog='========结束=========='
    )
    parser.add_argument('-c', '--conf')
    args = parser.parse_args()
    config_path :Path = Path(args.conf)
    asyncio.run(build(config_path))
