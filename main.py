import customtkinter as ctk
import threading
import time
import random
import os

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BeautifulVPN:
    def __init__(self):
        self.app = ctk.CTk()
        # state
        self.is_connected = False
        self.current_server = None

        # UI/state helpers
        # will hold tuples (server_dict, select_button, server_card)
        self.server_buttons = []
        # references to statistic value labels by key
        self.stat_value_labels = {}

        self.setup_window()
        self.load_data()
        self.create_ui()
        
    def setup_window(self):
        self.app.title("KingzVPN 🔒")
        self.app.geometry("900x700")
        self.app.minsize(800, 600)
        
        # Центрирование окна
        self.app.update_idletasks()
        x = (self.app.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.app.winfo_screenheight() // 2) - (700 // 2)
        self.app.geometry(f"900x700+{x}+{y}")
        
    def load_data(self):
        # Данные серверов
        self.servers = [
            {"name": "🇺🇸 США - Нью-Йорк", "ping": 28, "load": 45, "flag": "us"},
            {"name": "🇩🇪 Германия - Франкфурт", "ping": 35, "load": 32, "flag": "de"},
            {"name": "🇬🇧 Великобритания - Лондон", "ping": 42, "load": 28, "flag": "gb"},
            {"name": "🇯🇵 Япония - Токио", "ping": 128, "load": 65, "flag": "jp"},
            {"name": "🇸🇬 Сингапур", "ping": 185, "load": 41, "flag": "sg"},
            {"name": "🇨🇦 Канада - Торонто", "ping": 52, "load": 38, "flag": "ca"},
            {"name": "🇫🇷 Франция - Париж", "ping": 38, "load": 51, "flag": "fr"},
            {"name": "🇦🇺 Австралия - Сидней", "ping": 210, "load": 29, "flag": "au"}
        ]
        
        # Статистика
        self.stats = {
            "total_connections": 0,
            "total_time": 0,
            "data_used": 0
        }
        
    def create_gradient_bg(self):
        # Создаем фрейм с градиентом
        self.main_frame = ctk.CTkFrame(self.app, fg_color=("gray90", "gray10"))
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
    def create_header(self):
        # Верхняя панель
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=20)
        
        # Логотип и заголовок
        self.logo_label = ctk.CTkLabel(
            self.header_frame,
            text="🔒 KingzVPN",
            font=("Arial", 28, "bold"),
            text_color="#2b825b"
        )
        self.logo_label.pack(side="left")
        
        # Статус подключения
        self.status_indicator = ctk.CTkLabel(
            self.header_frame,
            text="● Отключено",
            font=("Arial", 14),
            text_color="#ff6b6b"
        )
        self.status_indicator.pack(side="right")
        
    def create_connection_card(self):
        # Карточка подключения
        self.connection_card = ctk.CTkFrame(
            self.main_frame, 
            corner_radius=20,
            fg_color=("gray85", "gray15")
        )
        self.connection_card.pack(fill="x", padx=20, pady=10)
        
        # Заголовок карточки
        card_title = ctk.CTkLabel(
            self.connection_card,
            text="Быстрое подключение",
            font=("Arial", 18, "bold")
        )
        card_title.pack(pady=(20, 10))
        
        # Кнопка подключения
        self.connect_button = ctk.CTkButton(
            self.connection_card,
            text="🔒 ПОДКЛЮЧИТЬСЯ",
            font=("Arial", 16, "bold"),
            height=50,
            fg_color="#2b825b",
            hover_color="#1f6b4a",
            command=self.toggle_connection
        )
        self.connect_button.pack(pady=20, padx=50, fill="x")
        
        # Прогресс бар
        self.progress_bar = ctk.CTkProgressBar(
            self.connection_card,
            height=4,
            fg_color="#2b825b",
            progress_color="#4CAF50"
        )
        self.progress_bar.pack(pady=10, padx=50, fill="x")
        self.progress_bar.set(0)
        
    def create_servers_section(self):
        # Секция выбора серверов
        servers_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        servers_frame.pack(fill="x", padx=20, pady=20)
        
        # Заголовок
        servers_title = ctk.CTkLabel(
            servers_frame,
            text="📍 Выберите сервер",
            font=("Arial", 18, "bold")
        )
        servers_title.pack(anchor="w", pady=(0, 10))
        
        # Фрейм для серверов с прокруткой
        self.servers_scrollable = ctk.CTkScrollableFrame(
            servers_frame,
            height=200,
            fg_color=("gray90", "gray13")
        )
        self.servers_scrollable.pack(fill="x", pady=10)
        
        # Создаем карточки серверов
        self.server_buttons = []
        for server in self.servers:
            self.create_server_card(server)
            
    def create_server_card(self, server):
        server_card = ctk.CTkFrame(
            self.servers_scrollable,
            corner_radius=15,
            fg_color=("gray85", "gray16")
        )
        server_card.pack(fill="x", pady=5, padx=5)
        
        # Основной контейнер
        content_frame = ctk.CTkFrame(server_card, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=10)
        
        # Информация о сервере
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        # Название сервера
        server_name = ctk.CTkLabel(
            info_frame,
            text=server["name"],
            font=("Arial", 14, "bold")
        )
        server_name.pack(anchor="w")
        
        # Статистика сервера
        stats_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        stats_frame.pack(anchor="w", pady=(5, 0))
        
        ping_label = ctk.CTkLabel(
            stats_frame,
            text=f"🏓 Пинг: {server['ping']}мс",
            font=("Arial", 11),
            text_color="#888"
        )
        ping_label.pack(side="left", padx=(0, 15))
        
        load_label = ctk.CTkLabel(
            stats_frame,
            text=f"📊 Нагрузка: {server['load']}%",
            font=("Arial", 11),
            text_color="#888"
        )
        load_label.pack(side="left")
        
        # Кнопка выбора
        select_btn = ctk.CTkButton(
            content_frame,
            text="Выбрать",
            width=80,
            height=30,
            fg_color="transparent",
            border_width=2,
            text_color=("gray30", "gray70"),
            border_color=("gray60", "gray40"),
            hover_color=("gray70", "gray30"),
            command=lambda s=server: self.select_server(s)
        )
        select_btn.pack(side="right")
        # Сохраняем привязку для быстрого изменения стиля при выборе
        self.server_buttons.append((server, select_btn, server_card))
        
    def create_stats_section(self):
        # Секция статистики
        stats_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=20)
        
        # Заголовок
        stats_title = ctk.CTkLabel(
            stats_frame,
            text="📈 Статистика",
            font=("Arial", 18, "bold")
        )
        stats_title.pack(anchor="w", pady=(0, 10))
        
        # Карточки статистики
        stats_cards_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_cards_frame.pack(fill="x")
        
        # Карточка 1 - Подключения
        card1, lbl1 = self.create_stat_card(
            stats_cards_frame,
            "🔗 Подключения",
            f"{self.stats['total_connections']}",
            "Всего сессий",
            "#2b825b"
        )
        card1.pack(side="left", fill="x", expand=True, padx=5)
        self.stat_value_labels['total_connections'] = lbl1
        
        # Карточка 2 - Время
        card2, lbl2 = self.create_stat_card(
            stats_cards_frame,
            "⏱️ Время",
            f"{self.stats['total_time']}ч",
            "Всего онлайн",
            "#2196F3"
        )
        card2.pack(side="left", fill="x", expand=True, padx=5)
        self.stat_value_labels['total_time'] = lbl2
        
        # Карточка 3 - Трафик
        card3, lbl3 = self.create_stat_card(
            stats_cards_frame,
            "📊 Трафик",
            f"{self.stats['data_used']}GB",
            "Использовано",
            "#FF9800"
        )
        card3.pack(side="left", fill="x", expand=True, padx=5)
        self.stat_value_labels['data_used'] = lbl3
        
    def create_stat_card(self, parent, title, value, subtitle, color):
        card = ctk.CTkFrame(
            parent,
            corner_radius=15,
            fg_color=("gray85", "gray16")
        )
        
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=("Arial", 12),
            text_color=color
        )
        title_label.pack(anchor="w")
        
        # Значение
        value_label = ctk.CTkLabel(
            content_frame,
            text=value,
            font=("Arial", 20, "bold")
        )
        value_label.pack(anchor="w", pady=(5, 0))
        
        # Подзаголовок
        subtitle_label = ctk.CTkLabel(
            content_frame,
            text=subtitle,
            font=("Arial", 10),
            text_color="#888"
        )
        subtitle_label.pack(anchor="w")
        return card, value_label
        
    def select_server(self, server):
        self.current_server = server
        # Визуальное выделение выбранного сервера — используем сохранённые кнопки
        for s, btn, card in self.server_buttons:
            try:
                if s.get("name") == server.get("name"):
                    btn.configure(
                        fg_color="#2b825b",
                        text_color="white",
                        hover_color="#1f6b4a"
                    )
                else:
                    btn.configure(
                        fg_color="transparent",
                        text_color=("gray30", "gray70"),
                        hover_color=("gray70", "gray30")
                    )
            except Exception:
                # безопасно игнорируем любые ошибки при обновлении стиля
                pass
        
    def toggle_connection(self):
        if not self.is_connected:
            self.connect_vpn()
        else:
            self.disconnect_vpn()
            
    def connect_vpn(self):
        if not self.current_server:
            # Автоматически выбираем лучший сервер
            best_server = min(self.servers, key=lambda x: x["ping"])
            self.select_server(best_server)
            
        self.is_connected = True
        self.connect_button.configure(
            text="🔓 ОТКЛЮЧИТЬСЯ",
            fg_color="#ff6b6b",
            hover_color="#ff5252",
            state="disabled"
        )
        
        # Запускаем анимацию подключения
        self.progress_bar.start()
        
        # Имитация подключения в отдельном потоке
        threading.Thread(target=self.simulate_connection, daemon=True).start()
        
    def disconnect_vpn(self):
        self.is_connected = False
        self.connect_button.configure(
            text="🔒 ПОДКЛЮЧИТЬСЯ",
            fg_color="#2b825b",
            hover_color="#1f6b4a",
            state="normal"
        )
        self.status_indicator.configure(text="● Отключено", text_color="#ff6b6b")
        self.progress_bar.stop()
        self.progress_bar.set(0)
        
        # Обновляем статистику
        self.stats["total_connections"] += 1
        self.stats["total_time"] += random.randint(1, 10)
        self.stats["data_used"] += round(random.uniform(0.1, 2.0), 1)
        self.update_stats()
        
    def simulate_connection(self):
        # Имитация процесса подключения
        steps = ["Установка соединения...", "Аутентификация...", "Шифрование...", "Подключено!"]
        
        for i, step in enumerate(steps):
            time.sleep(1.5)
            progress = (i + 1) / len(steps)
            
            self.app.after(0, self.update_connection_status, step, progress)
            
        # Подключение успешно
        self.app.after(0, self.connection_success)
        
    def update_connection_status(self, status, progress):
        self.status_indicator.configure(
            text=f"● {status}",
            text_color="#FFA500"  # Оранжевый во время подключения
        )
        self.progress_bar.set(progress)
        
    def connection_success(self):
        self.status_indicator.configure(
            text=f"● Подключено к {self.current_server['name']}",
            text_color="#4CAF50"  # Зеленый при успешном подключении
        )
        self.connect_button.configure(state="normal")
        self.progress_bar.stop()
        
    def update_stats(self):
        # Обновляем отображение статистики по сохранённым ссылкам на метки
        try:
            if 'total_connections' in self.stat_value_labels:
                self.stat_value_labels['total_connections'].configure(text=f"{self.stats['total_connections']}")
            if 'total_time' in self.stat_value_labels:
                self.stat_value_labels['total_time'].configure(text=f"{self.stats['total_time']}ч")
            if 'data_used' in self.stat_value_labels:
                self.stat_value_labels['data_used'].configure(text=f"{self.stats['data_used']}GB")
        except Exception:
            # не критично, укусим любые ошибки и продолжим
            pass
        
    def create_ui(self):
        self.create_gradient_bg()
        self.create_header()
        self.create_connection_card()
        self.create_servers_section()
        self.create_stats_section()
        
    def run(self):
        self.app.mainloop()

# Запуск приложения
if __name__ == "__main__":
    vpn_app = BeautifulVPN()
    vpn_app.run()