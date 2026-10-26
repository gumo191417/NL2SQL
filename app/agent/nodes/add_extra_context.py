from datetime import datetime

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState, DBInfoState
from app.core.log import logger


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "添加上下文", "status": "running"})
    try:
        today = datetime.today()
        date = today.strftime("%Y-%m-%d")
        weekday = today.strftime("%A")
        quarter = f"Q{(today.month - 1) // 3 + 1}"
        date_info = DateInfoState(
            date=date,
            weekday=weekday,
            quarter=quarter
        )
        dw_mysql_repository = runtime.context["dw_mysql_repository"]
        db_info: dict[str, str] = await dw_mysql_repository.get_db_info()
        db_info_state = DBInfoState(
            dialect=db_info["dialect"],
            version=db_info["version"]
        )
        writer({"type": "progress", "step": "添加上下文", "status": "success"})
        logger.info(f"额外上下文信息：{db_info}, {date_info}")
        return {"date_info": date_info, "db_info": db_info_state}
    except Exception as e:
        writer({"type": "progress", "step": "添加上下文", "status": "error"})
        logger.error(f"添加上下文失败, 错误信息: {str(e)}")
        raise









