"""
Сервер отображения картинок.
Запускается на ноутбуке, который должен показывать изображения.
Слушает команды по сети и меняет картинку по запросу.

Работает как из обычного .py, так и из собранного .exe (PyInstaller).
"""

import os
import sys
import socket
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


def get_images_folder() -> str:
    """
    Определяет, откуда брать картинки.

    Приоритет:
    1. Папка images/ рядом с .exe (или рядом со скриптом) — удобно менять картинки без пересборки
    2. Папка images/, упакованная внутрь .exe (если внешней нет)
    """
    # Папка, где лежит сам .exe или .py
    if getattr(sys, "frozen", False):
        # Запущено из .exe
        application_path = os.path.dirname(sys.executable)
    else:
        # Обычный запуск из исходников
        application_path = os.path.abspath(".")

    external_images = os.path.join(application_path, "images")

    # Если рядом с программой есть папка images — используем её
    if os.path.isdir(external_images):
        return external_images

    # Иначе пробуем взять картинки, которые были упакованы внутрь .exe
    try:
        bundled = os.path.join(sys._MEIPASS, "images")
        if os.path.isdir(bundled):
            return bundled
    except AttributeError:
        pass

    # В крайнем случае возвращаем внешний путь (даже если папки ещё нет)
    return external_images


# ==================== НАСТРОЙКИ ====================
PORT = 5555
IMAGES_FOLDER = get_images_folder()
WINDOW_TITLE = "Сервер картинок"
WINDOW_SIZE = "900x700"
# ===================================================


class ImageServer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.configure(bg="#1e1e2e")

        # Список путей к картинкам
        self.image_paths = self._load_image_paths()
        if not self.image_paths:
            messagebox.showerror(
                "Ошибка",
                "В папке «images» не найдено ни одной картинки!\n\n"
                "Положи туда файлы форматов:\n"
                ".jpg  .jpeg  .png  .gif  .bmp  .webp\n\n"
                "• При запуске из исходников — в папку images/ рядом с server.py\n"
                "• При запуске из .exe — создай папку images/ рядом с ImageServer.exe\n"
                "  и положи туда картинки (пересобирать не нужно)."
            )
            self.root.destroy()
            return

        self.current_index = 0
        self.photo = None  # Чтобы картинка не удалялась сборщиком мусора

        self._create_ui()
        self._show_current_image()

        # Запускаем сетевой сервер в отдельном потоке,
        # чтобы интерфейс не зависал
        self.server_thread = threading.Thread(
            target=self._run_network_server,
            daemon=True
        )
        self.server_thread.start()

        self.root.mainloop()

    def _load_image_paths(self) -> list[str]:
        """Собирает все поддерживаемые картинки из папки."""
        supported = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
        paths = []

        if not os.path.isdir(IMAGES_FOLDER):
            os.makedirs(IMAGES_FOLDER, exist_ok=True)
            return paths

        for name in sorted(os.listdir(IMAGES_FOLDER)):
            if name.lower().endswith(supported):
                paths.append(os.path.join(IMAGES_FOLDER, name))
        return paths

    def _create_ui(self):
        """Создаёт элементы интерфейса."""
        # Верхняя панель с информацией
        top_frame = tk.Frame(self.root, bg="#1e1e2e")
        top_frame.pack(fill=tk.X, padx=15, pady=10)

        self.info_label = tk.Label(
            top_frame,
            text="",
            font=("Segoe UI", 12),
            fg="#cdd6f4",
            bg="#1e1e2e",
        )
        self.info_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            top_frame,
            text="Ожидание подключений...",
            font=("Segoe UI", 11),
            fg="#a6e3a1",
            bg="#1e1e2e",
        )
        self.status_label.pack(side=tk.RIGHT)

        # Область с картинкой
        self.image_label = tk.Label(self.root, bg="#11111b")
        self.image_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        # Нижняя подсказка
        hint = tk.Label(
            self.root,
            text="Нажми кнопку на другом ноутбуке, чтобы сменить картинку",
            font=("Segoe UI", 10),
            fg="#6c7086",
            bg="#1e1e2e",
        )
        hint.pack(pady=(0, 15))

    def _show_current_image(self):
        """Отображает текущую картинку с масштабированием."""
        path = self.image_paths[self.current_index]
        name = os.path.basename(path)

        try:
            img = Image.open(path)

            # Масштабируем под размер окна (с небольшим запасом)
            max_w = self.root.winfo_width() - 60 or 800
            max_h = self.root.winfo_height() - 150 or 550

            img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)

            self.image_label.configure(image=self.photo)
            self.info_label.configure(
                text=f"Картинка {self.current_index + 1} из {len(self.image_paths)}  •  {name}"
            )
        except Exception as e:
            self.info_label.configure(text=f"Ошибка загрузки: {e}")

    def next_image(self):
        """Переключает на следующую картинку (вызывается из главного потока)."""
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self._show_current_image()
        self.status_label.configure(text="Картинка изменена!", fg="#89b4fa")
        # Через 2 секунды вернуть обычный статус
        self.root.after(2000, lambda: self.status_label.configure(
            text="Ожидание подключений...", fg="#a6e3a1"
        ))

    def _run_network_server(self):
        """Сетевой сервер в отдельном потоке."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", PORT))
            sock.listen(5)
            print(f"[Сервер] Слушаю порт {PORT}...")

            while True:
                conn, addr = sock.accept()
                print(f"[Сервер] Подключился: {addr}")

                try:
                    data = conn.recv(1024).decode("utf-8").strip()
                    if data == "next":
                        # Безопасно вызываем изменение картинки из GUI-потока
                        self.root.after(0, self.next_image)
                        conn.sendall(b"OK")
                    else:
                        conn.sendall(b"UNKNOWN")
                except Exception as e:
                    print(f"[Сервер] Ошибка обработки: {e}")
                finally:
                    conn.close()

        except Exception as e:
            print(f"[Сервер] Критическая ошибка: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Сетевая ошибка",
                f"Не удалось запустить сервер на порту {PORT}:\n{e}"
            ))


if __name__ == "__main__":
    ImageServer()
