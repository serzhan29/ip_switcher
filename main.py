import sys
import subprocess
import json
import os
import psutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QMessageBox, QInputDialog, QGroupBox, QGridLayout, QComboBox
)
from PyQt5.QtGui import QFont

CONFIG_FILE = "ip_config.json"


class IPManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IP Switcher")
        self.setGeometry(200, 200, 500, 350)

        # Определяем активный адаптер
        self.adapter = self.detect_adapter()
        if not self.adapter:
            QMessageBox.critical(self, "Ошибка", "❌ Не найден активный сетевой адаптер с IPv4")
            sys.exit(1)

        # Загружаем или создаём конфиг
        self.config = self.load_config()
        if not self.config:
            self.config = self.ask_config()
            self.save_config(self.config)

        # Основной layout
        layout = QVBoxLayout()

        self.label = QLabel(f"⚙️ Выбран адаптер: {self.adapter}")
        self.label.setFont(QFont("Arial", 12))
        layout.addWidget(self.label)

        # --- Блок кнопок ---
        btn_dhcp = QPushButton("Включить DHCP (локалка)")
        btn_dhcp.clicked.connect(self.set_dhcp)
        layout.addWidget(btn_dhcp)

        btn_static = QPushButton("Включить Статический IP (интернет)")
        btn_static.clicked.connect(self.set_static)
        layout.addWidget(btn_static)

        btn_edit = QPushButton("Изменить настройки")
        btn_edit.clicked.connect(self.edit_config)
        layout.addWidget(btn_edit)

        btn_change_adapter = QPushButton("Выбрать другой адаптер")
        btn_change_adapter.clicked.connect(self.change_adapter)
        layout.addWidget(btn_change_adapter)

        # --- Блок информации о текущих настройках ---
        info_group = QGroupBox("Текущие сохранённые настройки")
        info_layout = QGridLayout()

        self.ip_label = QLabel()
        self.mask_label = QLabel()
        self.gw_label = QLabel()
        self.dns_label = QLabel()

        info_layout.addWidget(QLabel("IP адрес:"), 0, 0)
        info_layout.addWidget(self.ip_label, 0, 1)

        info_layout.addWidget(QLabel("Маска подсети:"), 1, 0)
        info_layout.addWidget(self.mask_label, 1, 1)

        info_layout.addWidget(QLabel("Шлюз:"), 2, 0)
        info_layout.addWidget(self.gw_label, 2, 1)

        info_layout.addWidget(QLabel("DNS:"), 3, 0)
        info_layout.addWidget(self.dns_label, 3, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        self.setLayout(layout)

        # Обновляем инфо-панель
        self.update_info()

    def detect_adapter(self):
        """Определяем активный сетевой адаптер с IPv4"""
        adapters = []
        for adapter, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == 2 and not addr.address.startswith("169.254"):  # IPv4 + не APIPA
                    adapters.append(adapter)

        if not adapters:
            return None
        elif len(adapters) == 1:
            return adapters[0]
        else:
            # Если несколько адаптеров — спросим у пользователя
            adapter, ok = QInputDialog.getItem(
                self, "Выбор адаптера", "Найдено несколько адаптеров. Выберите один:", adapters, 0, False
            )
            return adapter if ok else None

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return None

    def save_config(self, config):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

    def ask_config(self):
        ip, _ = QInputDialog.getText(self, "IP", "Введите статический IP:")
        mask, _ = QInputDialog.getText(self, "Маска", "Введите маску подсети:", text="255.255.255.0")
        gw, _ = QInputDialog.getText(self, "Шлюз", "Введите шлюз:")
        dns, _ = QInputDialog.getText(self, "DNS", "Введите DNS:", text="8.8.8.8")
        return {"STATIC_IP": ip, "SUBNET_MASK": mask, "GATEWAY": gw, "DNS": dns}

    def set_dhcp(self):
        subprocess.run(f'netsh interface ip set address name="{self.adapter}" source=dhcp', shell=True)
        subprocess.run(f'netsh interface ip set dns name="{self.adapter}" source=dhcp', shell=True)
        QMessageBox.information(self, "Успех", f"✅ DHCP включён на {self.adapter}")

    def set_static(self):
        cfg = self.config
        subprocess.run(
            f'netsh interface ip set address name="{self.adapter}" static {cfg["STATIC_IP"]} {cfg["SUBNET_MASK"]} {cfg["GATEWAY"]}',
            shell=True
        )
        subprocess.run(f'netsh interface ip set dns name="{self.adapter}" static {cfg["DNS"]}', shell=True)
        QMessageBox.information(self, "Успех", f'✅ Статический IP включён: {cfg["STATIC_IP"]}')

    def edit_config(self):
        self.config = self.ask_config()
        self.save_config(self.config)
        self.update_info()
        QMessageBox.information(self, "Обновлено", "⚙️ Настройки сохранены.")

    def change_adapter(self):
        """Позволяет выбрать другой адаптер"""
        adapters = list(psutil.net_if_addrs().keys())
        adapter, ok = QInputDialog.getItem(self, "Смена адаптера", "Выберите адаптер:", adapters, 0, False)
        if ok and adapter:
            self.adapter = adapter
            self.label.setText(f"⚙️ Выбран адаптер: {self.adapter}")
            QMessageBox.information(self, "Готово", f"🔄 Теперь выбран адаптер: {self.adapter}")

    def update_info(self):
        """Обновляем отображение конфигурации в окне"""
        if self.config:
            self.ip_label.setText(self.config.get("STATIC_IP", "—"))
            self.mask_label.setText(self.config.get("SUBNET_MASK", "—"))
            self.gw_label.setText(self.config.get("GATEWAY", "—"))
            self.dns_label.setText(self.config.get("DNS", "—"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IPManager()
    window.show()
    sys.exit(app.exec_())
