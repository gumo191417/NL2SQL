from dataclasses import asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.conversions.common_types import QueryResponse, VectorParams, Distance, PointStruct

from app.conf.app_config import app_config
from app.entities.metric_info import MetricInfo


class MetricQdrantRepository:
    COLLECTION_NAME = "data-agent-metric"

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def ensure_collection(self):
        if not await self.client.collection_exists(collection_name=self.COLLECTION_NAME):
            await self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE
                )
            )

    async def upsert(self, ids: list[str], payloads: list[MetricInfo], embededs: list[list[float]],
                     batch_size: int = 10):
        """分批次 批量新增向量点到qdrant"""
        # 1. 通过zip函数将id、payload、embedded三者按索引位置打包成元组列表，将zip迭代器对象转换为列表
        zipped = list(zip(ids, payloads, embededs))
        # 2. 采用分批次构建
        for i in range(0, len(zipped), batch_size):
            batch = zipped[i:i + batch_size]
            points = [PointStruct(
                id=id,
                payload=asdict(payload),
                vector=vector
            ) for id, payload, vector in batch]
            # 3. 将本批次的向量点存入到集合中
            await self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points
            )

    async def search(self, embedding: list[float], score_threshold: float = 0.6, limit: int = 10) -> list[MetricInfo]:
        """获取语义相似指标信息"""
        result: QueryResponse = await self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=embedding,
            score_threshold=score_threshold,
            limit=limit
        )
        return [MetricInfo(**point.payload) for point in result.points]