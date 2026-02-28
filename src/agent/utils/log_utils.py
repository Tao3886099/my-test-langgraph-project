import sys,os
from loguru import logger

# 获取当前文件的绝对路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(root_dir, 'logs')

# 如果日志目录不存在，则创建它
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

class MyLogger:
    def __init__(self):
        self.logger = logger
        self.logger.remove()
        self.logger.add(sys.stdout, colorize=True, level="DEBUG",
                        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                               "{process.name} | " #进程名
                               "{thread.name} | " #线程名
                               "<cyan>{module}</cyan>.<cyan>{function}</cyan> | "
                               "<cyan>{line}</cyan> | "
                               "<level>{level}</level>"
                               "<level>{message}</level>"
                        )

    def get_logger(self):
        return self.logger

log = MyLogger().get_logger()


if __name__ == "__main__":
    log.debug("debug")
    log.info("info")
    log.warning("warning")
    log.error("error")
    print('str.pdf'['str.pdf'.rindex('.'):])

    def test():
        try:
            print(3 / 0)
        except ZeroDivisionError as e:
            log.error(f"发生错误: {e}")

    test()