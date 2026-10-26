import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate, load_prompt
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type":"progress","step":"过滤表", "status":"running"})
    query = state["query"]
    table_infos = state["table_infos"]
    prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=["query", "table_infos"])
    chain = prompt | llm | JsonOutputParser()
    result = await chain.ainvoke(
        {"query": query, "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False)})
    for table_info in table_infos[:]:
        table_name = table_info["name"]
        if table_name not in result:
            table_infos.remove(table_info)
        else:
            for column in table_info["columns"][:]:
                column_name = column["name"]
                if column_name not in result[table_name]:
                    table_info["columns"].remove(column)
    writer({"type": "progress", "step": "过滤表", "status": "success"})
    logger.info(f"过滤表成功：{[table_info['name'] for table_info in table_infos]}")
    logger.info(f"过滤字段成功：{[column['name'] for table_info in table_infos for column in table_info['columns']]}")
    # 4.更新state中表格信息
    return {"table_infos": table_infos}