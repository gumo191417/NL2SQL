import uuid
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledgeService:
    def __init__(self,meta_mysql_repository: MetaMySQLRepository,dw_mysql_repository:DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository, embedding_client:HuggingFaceEndpointEmbeddings,
                 value_es_repository:ValueESRepository,metric_qdrant_repository: MetricQdrantRepository):
        """封装业务逻辑层所需要依赖对象-操作各种 库（MySQL，ES，Qdrant） 持久层对象"""
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def build(self, meta_config_path: Path):
        """
        1.加载配置文件


        2.处理表信息
        2.1 保存表信息到meta数据库
        2.2 为字段信息建立向量索引
        2.3 为字段取值建立全文索引

        3.处理指标信息
        3.1 保存指标信息到meta数据库
        3.2 为指标信息建立向量索引

        :param meta_config_path: 参数文件path对象
        """
        logger.info(f"构建元数据库脚本,{meta_config_path}")
        context = OmegaConf.load(meta_config_path)
        structured = OmegaConf.structured(MetaConfig)


        meta_config:MetaConfig = OmegaConf.to_object(OmegaConf.merge(structured, context))

        # 处理表格信息
        if meta_config.tables:
            # 将表格（表信息、字段信息）信息存入到meta元数据库
            column_infos: list[ColumnInfo] = await self._save_table_info_to_meta_db(meta_config)
            logger.info(f"批量保存表信息成功")

            # 为字段信息建立向量索引 存入 Qdrant
            await self._save_column_info_to_qdrant(column_infos)
            logger.info(f"为字段信息建立向量索引成功")

            # 为字段取值建立全文索引 存入 ES
            await self._save_value_info_to_es(meta_config,column_infos)
            logger.info(f"为字段取值建立全文索引成功 ")
        # 3. 处理指标信息
        if meta_config.metrics:
            # 将指标信息存入到meta元数据库
            metric_infos: list[MetricInfo] = await self._save_metric_info_to_meta_db(meta_config)
            logger.info("指标信息存入到meta元数据库成功")

            #  3.2 为指标信息建立向量索引 存入 Qdrant
            await self._save_metric_info_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引成功")

            pass
    async def _save_table_info_to_meta_db(self,meta_config:MetaConfig) -> list[ColumnInfo]:
        """ 构建持久层保存表格信息需要列表对象，调用meta数据库持久层批量新增 """
        # 初始化存放表信息、字段信息列表 信息一部分来自配置文件、另一部分来自DW数仓(字段类型、部分事例值)
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []
        # 处理表信息，从元信息对象中获取表信息列表，将表信息加入到表信息列表中
        if meta_config.tables:
            for table in meta_config.tables:
                table_info = TableInfo(
                    id=table.name,
                    name=table.name,
                    description=table.description,
                    role=table.role
                )

                table_infos.append(table_info)

                # 查询DW库，根据表ID获取表所有字段类型
                column_type: dict[str,str] = await self.dw_mysql_repository.get_column_type_by_table_id(table_info.id)
                for column in table.columns:
                    # 查询DW库，查询某张表某个字段部分取值
                    examples :list[str] = await self.dw_mysql_repository.get_column_value_by_table_id(table_info.id,column.name)

                    column_info = ColumnInfo(
                        id=f"{table_info.id}.{column.name}",
                        name =column.name,
                        type=column_type[column.name],
                        role=column.role,
                        examples =examples,
                        description=column.description,
                        alias=column.alias,
                        table_id=table_info.id
                    )
                    column_infos.append(column_info)
        # 调用meta持久层对象 完成批量新增到meta数据库 手动开启事务
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_table_infos(table_infos)
            await self.meta_mysql_repository.save_column_infos(column_infos)
        return column_infos

    async def _save_column_info_to_qdrant(self, column_infos:list[ColumnInfo]):
        await self.column_qdrant_repository.ensure_collection()


        # 准备向量库持久层所需要向量数据点 ID，向量，元数据（业务数据）
        points=[]
        for column_info in column_infos:
            points.append({
                "id": uuid.uuid4(),
                "embedding_text":column_info.name,
                "payload": column_info
            })
            points.append({
                "id":uuid.uuid4(),
                "embedding-text":column_info.description,
                "payload":column_info
            })
            for alias in column_info.alias:
                points.append({
                    "id":uuid.uuid4(),
                    "embedding-text":alias,
                    "payload":column_info
                })
        embeddings = []
        batch_size = 10
        embedding_texts = [point["embedding_text"] for point in points]
        for i in range(0,len(embedding_texts) ,batch_size):
            batch_embedding = embedding_texts[i:i+batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding)
            embeddings.extend(batch_embeddings)
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_value_info_to_es(self, meta_config: MetaConfig, column_infos:list[ColumnInfo]):
        await self.value_es_repository.ensure_index()
        value_infos:list[ValueInfo] = []
        # 从人工配置元信息得到需要同步到ES字段列表
        column2es = []
        for table in meta_config.tables:
            for column in table.columns:
                if column.sync == True:
                    column2es.append(column)

        # 遍历字段列表，查询出字段枚举值
        for column_info in column_infos:
            if column_info.name in column2es:
                values = await self.dw_mysql_repository.get_column_value_by_table_id(column_info.table_id,column_info.name,
                                                                                     limit=1000000)
                for value in values:
                    value_info = ValueInfo(
                        id=f"{column_info.id}.{value}",
                        value=value,
                        column_id=column_info.id
                    )
                    value_infos.append(value_info)

        await self.value_es_repository.upsert(value_infos)

    async def _save_metric_info_to_meta_db(self, meta_config:MetaConfig) -> list[MetricInfo]:
        metric_infos :list[MetricInfo] = []
        column_metrics:list[ColumnMetric] = []

        for metric in meta_config.metrics:
            metric_info = MetricInfo(
                id = metric.name,
                name = metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias
            )
            metric_infos.append(metric_info)
            for relevant_column in metric.relevant_columns:
                column_metric = ColumnMetric(
                    metric_id=metric_info.id,
                    column_id=relevant_column
                )
                column_metrics.append(column_metric)
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_info_to_meta_db(metric_infos)
            await self.meta_mysql_repository.save_column_metric_info_to_meta_db(column_metrics)
        return metric_infos

    async def _save_metric_info_to_qdrant(self, metric_infos:list[MetricInfo]):
        await self.metric_qdrant_repository.ensure_collection()
        points = []
        for metric_info in metric_infos:
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": metric_info.name,
                "payload": metric_info
            })
            points.append({
                "id": uuid.uuid4(),
                "embedding_text": metric_info.description,
                "payload": metric_info
            })
            for alias in metric_info.alias:
                points.append({
                    "id": uuid.uuid4(),
                    "embedding_text": alias,
                    "payload": metric_info
                })

        embeddings = []
        batch_size = 10
        embedding_texts = [point["embedding_text"] for point in points]
        for i in range(0, len(embedding_texts), batch_size):
            batch_embedding = embedding_texts[i: i + batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding)
            embeddings.extend(batch_embeddings)
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        # 3. 调用字段信息向量库持久层批量保存
        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)
        pass




















