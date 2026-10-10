"""
Клиент с кнопкой.
Запускается на ноутбуке, с которого нужно управлять картинкой.
При нажатии кнопки отправляет команду серверу.
"""

import socket
import tkinter as tk
from tkinter import messagebox


# ==================== НАСТРОЙКИ ====================
DEFAULT_PORT = 5555
WINDOW_TITLE = "Управление картинкой"
WINDOW_SIZE = "420x320"
# ===================================================


class ImageClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self._create_ui()
        self.root.mainloop()

    def _create_ui(self):
        # Заголовок
        title = tk.Label(
            self.root,
            text="Смена картинки",
            font=("Segoe UI", 18, "bold"),
            fg="#cdd6f4",
            bg="#1e1e2e",
        )
        title.pack(pady=(25, 5))

        subtitle = tk.Label(
            self.root,
            text="Введи IP-адрес ноутбука с картинками",
            font=("Segoe UI", 10),
            fg="#6c7086",
            bg="#1e1e2e",
        )
        subtitle.pack(pady=(0, 15))

        # Поле ввода IP
        ip_frame = tk.Frame(self.root, bg="#1e1e2e")
        ip_frame.pack(pady=5)

        tk.Label(
            ip_frame,
            text="IP:",
            font=("Segoe UI", 11),
            fg="#cdd6f4",
            bg="#1e1e2e",
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.ip_entry = tk.Entry(
            ip_frame,
            font=("Consolas", 12),
            width=18,
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief=tk.FLAT,
            justify=tk.CENTER,
        )
        self.ip_entry.pack(side=tk.LEFT)
        self.ip_entry.insert(0, "192.168.1.")  # Подсказка типичного локального адреса

        # Кнопка
        self.button = tk.Button(
            self.root,
            text="Сменить картинку",
            font=("Segoe UI", 14, "bold"),
            bg="#89b4fa",
            fg="#1e1e2e",
            activebackground="#74c7ec",
            activeforeground="#1e1e2e",
            relief=tk.FLAT,
            padx=30,
            pady=12,
            cursor="hand2",
            command=self._send_command,
        )
        self.button.pack(pady=25)

        # Статус
        self.status_label = tk.Label(
            self.root,
            text="Готов к работе",
            font=("Segoe UI", 10),
            fg="#a6e3a1",
            bg="#1e1e2e",
        )
        self.status_label.pack(pady=5)

        # Подсказка внизу
        hint = tk.Label(
            self.root,
            text="Узнать IP можно командой ipconfig (Windows)\nили ifconfig / ip a (Linux/Mac)",
            font=("Segoe UI", 9),
            fg="#585b70",
            bg="#1e1e2e",
            justify=tk.CENTER,
        )
        hint.pack(side=tk.BOTTOM, pady=15)

    def _send_command(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showwarning("Внимание", "Введи IP-адрес сервера!")
            return

        self.status_label.configure(text="Отправка...", fg="#f9e2af")
        self.root.update()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)  # 3 секунды на подключение
                sock.connect((ip, DEFAULT_PORT))
                sock.sendall(b"next")
                response = sock.recv(1024)

            if response == b"OK":
                self.status_label.configure(text="Готово! Картинка изменена", fg="#a6e3a1")
            else:
                self.status_label.configure(text="Сервер ответил странно", fg="#f9e2af")

        except socket.timeout:
            self.status_label.configure(text="Таймаут. Проверь IP и сеть", fg="#f38ba8")
        except ConnectionRefusedError:
            self.status_label.configure(
                text="Сервер не запущен или порт закрыт", fg="#f38ba8"
            )
        except OSError as e:
            self.status_label.configure(text=f"Ошибка сети: {e}", fg="#f38ba8")
        except Exception as e:
            self.status_label.configure(text=f"Ошибка: {e}", fg="#f38ba8")


if __name__ == "__main__":
    ImageClient()
