from argparse import ArgumentParser
from pathlib import Path

from app.core.log import logger
def build(config:Path):
    """
    构建元知识库函数
    用于执行构建元知识相关的业务逻辑，例如加载配置、初始化数据等
    """
    # 打印INFO级别的日志，记录当前正在执行的操作
    logger.info("Building meta knowledge...")
    logger.info(str(config))


# 判断当前脚本是否作为主程序运行
if __name__ == '__main__':
    # 调用build函数，执行元知识构建逻辑
    parser = ArgumentParser(
        prog='python -m app.scripts.build_meta_knowledge',
        description='通过脚本+额外脚本(-c 传递)参数实现',
        epilog='========结束=========='
    )
    parser.add_argument('-c', '--conf')
    args = parser.parse_args()
    config_path :Path = Path(args.conf)
    build(Path(args.conf))