from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.entities.value_info import ValueInfo


class ValueESRepository:
    """操作字段取值ES持久层类"""
    idx_name = "data-agent-column"
    es_index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def ensure_index(self):
        if not await self.client.indices.exists(index=self.idx_name):
            await self.client.indices.create(
                index=self.idx_name,
                mappings=self.es_index_mappings
            )

    async def upsert(self, value_infos: list[ValueInfo],batch_size=10):
        for i in range(0,len(value_infos),batch_size):
            batch = value_infos[i:i + batch_size]
            operation:list = []
            for value_info in batch:
                operation.append({
                    "index":{
                        "_index":self.idx_name,
                        "_id":value_info.id
                    }
                })
                operation.append(asdict(value_info))
                await self.client.bulk(operations=operation)