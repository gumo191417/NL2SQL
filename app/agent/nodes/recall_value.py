from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate, load_prompt
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo


async def recall_value(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})

    try:
        query = state.get("query")
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"),input_variables=["query"])
        chain = prompt | llm | JsonOutputParser()

        result = await chain.ainvoke({"query":query})
        keywords = state.get("keywords")
        keywords = list(set(keywords + result))
        retrieved_value_map :dict[str,ValueInfo] = {}
        value_es_repository = runtime.context["value_es_repository"]
        for keyword in keywords:
            value_infos = value_es_repository.search(keyword)
            for value_info in value_infos:
                value_info_id = value_info.id
                if value_info_id not in retrieved_value_map:
                    retrieved_value_map[value_info_id] = value_info
        writer({"type": "progress", "step": "召回字段取值", "status": "success"})
        logger.info(f"召回字段取值成功：{list(retrieved_value_map.keys())}")
        return {"retrieved_values":list(retrieved_value_map.values())}
    except Exception as e:
        writer({"type": "progress", "step": "召回字段取值", "status": "error"})
        logger.error(f"召回字段取值失败, 错误信息: {str(e)}")
        raise
