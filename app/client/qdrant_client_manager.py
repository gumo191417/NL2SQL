import asyncio
import random

from app.conf.app_config import app_config,QdrantConfig
from typing import Optional
from qdrant_client import AsyncQdrantClient,models

class QdrantClientManager:
    def __init__(self,qdrant_config:QdrantConfig):
        self.qdrant_config =qdrant_config
        self.client :Optional[AsyncQdrantClient] = None

    def _get_url(self):
        return f"http://{self.qdrant_config.host}:{self.qdrant_config.port}"

    def init(self):
        """初始化异步Qdrant客户端（创建客户端实例）"""
        self.client = AsyncQdrantClient(self._get_url())

    async def close(self):
        await self.client.close()



if __name__ == '__main__':
    qdrant_client_manager = QdrantClientManager(app_config.qdrant)
    qdrant_client_manager.init()
    async def test():
        client = qdrant_client_manager.client
        if not await client.collection_exists("my_collection"):
            await client.create_collection(
                collection_name="my_collection",
                vectors_config=models.VectorParams(size=10, distance=models.Distance.COSINE)
            )
        await client.upsert(
            collection_name="my_collection",
            points=[
                models.PointStruct(
                    id=i,
                    vector=[random.random() for _ in range(10)]
                )
                for i in range(100)
            ]
        )
        res = await client.query_points(
            collection_name="my_collection",  # 检索的集合名称
            query=[random.random() for _ in range(10)],  # 10维随机查询向量（type: ignore忽略类型提示）
            limit=10,  # 返回最相似的前10个向量
            score_threshold=0.95  # 相似度得分阈值：只返回得分≥0.5的结果
        )
        # 打印检索结果中的向量点信息（包含ID、向量、得分等）
        print(res.points)
    asyncio.run(test())