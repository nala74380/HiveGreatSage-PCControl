from core.utils.adb_manager import AdbManager

class Application:
    def __init__(self):
        ...
        self.adb = AdbManager()
        self.adb.start_server()   # 拉起 adb server