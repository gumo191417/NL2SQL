import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate, load_prompt
from langgraph.runtime import Runtime

import prompt
from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type":"progress", "step":"过滤指标", "status":"running"})

    try:
        metric_infos = state.get("metric_infos")
        query = state.get("query")
        prompt = PromptTemplate(template=load_prompt("filter_metric_info"),input_variables=["query","metric_infos"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query":query,"metric_infos":yaml.dump(metric_infos,allow_unicode=True,sort_keys=False)})
        for metric_info in metric_infos[:]:
            metric_name = metric_info["name"]
            if metric_name not in result:
                metric_infos.remove(metric_info)
        writer({"type": "progress", "step": "过滤指标", "status": "success"})
        logger.info(f"过滤指标成功：{[metric_info["name"] for metric_info in metric_infos]}")
        return {"metric_infos": metric_infos}
    except Exception as e:
        writer({"type": "progress", "step": "过滤指标", "status": "error"})
        logger.error(f"过滤指标失败, 错误信息: {str(e)}")
        raise


