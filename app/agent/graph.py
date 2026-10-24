from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agent.context import DataAgentContext
from app.agent.nodes import extract_keywords, recall_column, recall_value, recall_metric, merge_retrieved_info, \
    filter_table, filter_metric, add_extra_context, generate_sql, validate_sql, correct_sql, execute_sql
from app.agent.state import DataAgentState

# 构建图
graph_builder = StateGraph(state_schema=DataAgentState,context_schema=DataAgentContext)

# 添加节点
graph_builder.add_node("extract_keywords",extract_keywords)
graph_builder.add_node("recall_column",recall_column)
graph_builder.add_node("recall_value",recall_value)
graph_builder.add_node("recall_metric",recall_metric)
graph_builder.add_node("merge_retrieved_info",merge_retrieved_info)
graph_builder.add_node("filter_table",filter_table)
graph_builder.add_node("filter_metric",filter_metric)
graph_builder.add_node("add_extra_context",add_extra_context)
graph_builder.add_node("generate_sql",generate_sql)
graph_builder.add_node("validate_sql",validate_sql)
graph_builder.add_node("correct_sql",correct_sql)
graph_builder.add_node("execute_sql",execute_sql)

# 添加关系
graph_builder.add_edge(START,"extract_keywords")
graph_builder.add_edge("extract_keywords","recall_column")
graph_builder.add_edge("extract_keywords","recall_value")
graph_builder.add_edge("extract_keywords","recall_metric")
graph_builder.add_edge("recall_column","merge_retrieved_info")
graph_builder.add_edge("recall_value","merge_retrieved_info")
graph_builder.add_edge("recall_metric","merge_retrieved_info")
graph_builder.add_edge("merge_retrieved_info","filter_table")
graph_builder.add_edge("merge_retrieved_info","filter_metric")
graph_builder.add_edge("filter_table","add_extra_context")
graph_builder.add_edge("filter_metric","add_extra_context")
graph_builder.add_edge("add_extra_context","generate_sql")
graph_builder.add_edge("generate_sql","validate_sql")
graph_builder.add_conditional_edges("validate_sql",lambda state:"execute_sql" if state["error"]
is None else "correct_sql",{"execute_sql":"execute_sql","correct_sql":"correct_sql"})
graph_builder.add_edge("correct_sql","execute_sql")
graph_builder.add_edge("execute_sql",END)


# 编译图--获取全局graph对象
graph=graph_builder.compile()

if __name__ == '__main__':
    # 查看图构建的形状 draw_mermaid-->文本画图的方式
    print(graph.get_graph().draw_mermaid())