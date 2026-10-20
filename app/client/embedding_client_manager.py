from typing import Optional
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from app.conf.app_config import EmbeddingConfig,app_config

class EmbeddedClientManager:
    def __init__(self,config:EmbeddingConfig):
        self.config =config
        self.client : Optional[HuggingFaceEndpointEmbeddings] = None

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = HuggingFaceEndpointEmbeddings(model=self._get_url())




# 主程序入口：测试嵌入式客户端功能
if __name__ == '__main__':
    embedding_client_manager = EmbeddedClientManager(app_config.embedding)
    # 创建 EmbeddedClientManager 实例
    client = EmbeddedClientManager(app_config.embedding)
    # 初始化嵌入客户端
    client.init()
    # 对文本 "hello world" 进行向量嵌入
    query = client.client.embed_query("hello world")
    # 打印嵌入向量的长度
    print(len(query))
    # 打印嵌入向量的具体值
    print(query)