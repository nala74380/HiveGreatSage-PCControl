# ui/widgets/device_table_widget.py

def on_activate(self, serial: str):
    ok, msg = self.app.adb.activate_device(serial)
    if ok:
        QMessageBox.information(self, "激活成功", f"{serial}\n{msg}")
    else:
        QMessageBox.warning(self, "激活失败", f"{serial}\n{msg}")
    self.refresh_table()   # 刷新激活状态列

def on_enable_tcpip(self, serial: str):
    """右键菜单 → 切换为 TCP/IP 模式"""
    ip = self.app.adb.get_ip_address(serial)
    if not ip:
        QMessageBox.warning(self, "错误", "无法获取 WiFi 地址，请确认设备已连接 WiFi")
        return
    self.app.adb.enable_tcpip(serial)
    QMessageBox.information(self, "TCP/IP 模式", f"已切换\n设备 IP: {ip}:5555\n可拔 USB，使用菜单「TCP连接」重新连入")