from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate, load_prompt
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo


async def recall_metric(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})

    try:
        query = state.get("query")
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"),input_variables=["query"])
        chain = prompt | llm | JsonOutputParser
        result = await chain.ainvoke({"query":query})
        logger.info(f"对原查询llm扩展后指标列表：{result}")
        keywords = state.get("keywords")
        keywords = list(set(keywords + result))
        retrieved_metric_map: dict[str, MetricInfo] = {}
        embedding_client = runtime.context["embedding_client"]
        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
        for keyword in keywords:
            embedding = await embedding_client.aembed_query(keyword)
            metric_infos : list[MetricInfo] = await metric_qdrant_repository.search(embedding)
            for metric_info in metric_infos:
                metric_info_id = metric_info.id
                if metric_info_id not in retrieved_metric_map:
                    retrieved_metric_map[metric_info_id] = metric_info
        writer({"type": "progress", "step": "召回指标", "status": "success"})
        logger.info(f"召回指标成功：{list(retrieved_metric_map.keys())}")
        return{"retrieved_metric_map":list(retrieved_metric_map.values())}
    except Exception as e:
        logger.error(f"召回指标失败, 错误信息: {str(e)}")
        writer({"type": "progress", "step": "召回指标", "status": "error"})
        raise



