from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState, ColumnInfoState, MetricInfoState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "合并信息", "status": "running"})
    try:
        retrieved_columns = state.get("retrieved_columns")

        retrieved_metrics = state.get("retrieved_metrics")
        retrieved_values = state.get("retrieved_values")
        retrieved_columns_map:dict[str,ColumnInfo] = {retrieved_column.id :retrieved_column for retrieved_column in retrieved_columns}
        meta_mysql_repository = runtime.context["meta_mysql_repository"]
        for retrieved_metric in retrieved_metrics:
            for metric_column_id in retrieved_metric.relevant_columns:
                if metric_column_id not in retrieved_columns_map:
                    column_info:ColumnInfo = await meta_mysql_repository.get_column_info_by_id(metric_column_id)
                    retrieved_columns_map[metric_column_id] = column_info

        for value_info in retrieved_values:
            column_id = value_info.column_id
            if column_id not in retrieved_columns_map:
                column_info: ColumnInfo = await meta_mysql_repository.get_column_info_by_id(column_id)
                retrieved_columns_map[column_id] = column_info

            value = value_info.value
            if value not in retrieved_columns_map[column_id].examples:
                retrieved_columns_map[column_id].examples.append(value)

            table_id_to_columns_map: dict[str, list[ColumnInfo]] = {}
            for column_info in retrieved_columns_map.values():
                table_id = column_info.table_id
                if table_id not in table_id_to_columns_map:
                    table_id_to_columns_map[table_id] = []
                table_id_to_columns_map[table_id].append(column_info)

            for table_id in table_id_to_columns_map.keys():
                columns: list[str] = [column_info.id for column_info in table_id_to_columns_map[table_id]]
                key_columns: list[ColumnInfo] = await meta_mysql_repository.get_key_column_by_table_id(table_id)
                for key_column in key_columns:
                    key_column_id = key_column.id
                    if key_column_id not in columns:
                        table_id_to_columns_map[table_id].append(key_column)
            table_infos: list[TableInfoState] = []
            for table_id, column_infos in table_id_to_columns_map.items():
                table_info: TableInfo = await meta_mysql_repository.get_table_info_by_id(table_id)
                table_info_state = TableInfoState(
                    name=table_info.name,
                    role=table_info.role,
                    description=table_info.description,
                    # 4.2 处理表中字段：将列表list[ColumnInfo]转为list[ColumnInfoState]
                    columns=[ColumnInfoState(
                        name=column_info.name,
                        type=column_info.type,
                        role=column_info.role,
                        examples=column_info.examples,
                        description=column_info.description,
                        alias=column_info.alias
                    ) for column_info in column_infos]
                )
                table_infos.append(table_info_state)
            logger.info(f"合并信息，表列表：{[table["name"] for table in table_infos]}")
            logger.info(f"合并信息，字段列表：{[column["name"] for table in table_infos for column in table["columns"]]}")
            metric_infos: list[MetricInfoState] = [MetricInfoState(
                name=retrieved_metric.name,
                description=retrieved_metric.description,
                relevant_columns=retrieved_metric.relevant_columns,
                alias=retrieved_metric.alias
            ) for retrieved_metric in retrieved_metrics]
            writer({"type": "progress", "step": "合并信息", "status": "success"})
            logger.info(f"合并信息，指标列表：{[metric_info["name"] for metric_info in metric_infos]}")
            return {"metric_infos": metric_infos, "table_infos": table_infos}
    except Exception as e:
        writer({"type": "progress", "step": "合并信息", "status": "error"})
        logger.error(f"合并信息失败, 错误信息: {str(e)}")
        raise




















