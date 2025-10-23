import customtkinter as ctk
import requests
from requests.exceptions import RequestException
import urllib3
import base64
import json
from json.decoder import JSONDecodeError
import re
import threading
from threading import Event, Lock
import time
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired, check_output as subprocess_check_output
import os
from os import path
import psutil
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Union, Tuple
from queue import Queue

# Setup app directories
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(APP_DIR, 'vpn_configs')
LOG_DIR = os.path.join(APP_DIR, 'logs')
for d in [CONFIG_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernVPNClient:
    def __init__(self):
        self.app = ctk.CTk()
        self.setup_window()
        self.configs = []
        self.current_config = None
        self.vpn_process = None
        self.is_connected = False
        
        # Защита от множественных попыток подключения
        self.connection_lock = threading.Lock()
        # Для мониторинга процесса OpenVPN
        self.process_output = []
        self.openvpn_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vpn_configs')
        if not os.path.exists(self.openvpn_config_path):
            os.makedirs(self.openvpn_config_path)

        # События для контроля потоков
        self.events = {
            'stats_stop': Event(),
            'monitor_stop': Event(),
            'process_stop': Event()
        }
        
        # Хранение активных потоков для корректного завершения
        self.active_threads = {
            'monitor': None,
            'stats': None,
            'process': None
        }
        
        # Очередь для безопасной передачи данных между потоками
        self.stats_queue = Queue(maxsize=100)
        
        # Для хранения прямых ссылок на виджеты скорости
        self.speed_widgets = {
            'download': None,  # download_label
            'upload': None,    # upload_label
            'ping': None      # ping_label
        }
        
        # Логирование
        self.setup_logging()
        
        # Цветовая схема
        self.colors = {
            "primary": "#2b825b",
            "secondary": "#2196F3", 
            "success": "#4CAF50",
            "warning": "#FF9800",
            "danger": "#ff6b6b",
            "dark_bg": "#1a1a1a",
            "card_bg": ("#2d2d2d", "#1e1e1e")
        }
        
        self.load_data()
        self.create_ui()
        
    def setup_window(self):
        self.app.title("🔒 KingzVPN - Secure Connection")
        self.app.geometry("1200x800")
        self.app.minsize(1000, 700)
        
        # Центрирование окна
        self.app.update_idletasks()
        x = (self.app.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.app.winfo_screenheight() // 2) - (800 // 2)
        self.app.geometry(f"1200x800+{x}+{y}")
        
    def load_data(self):
        # Предустановленные серверы
        self.preset_servers = [
            {"name": "🇺🇸 США - Нью-Йорк", "ping": 28, "load": 45, "flag": "us", "type": "preset"},
            {"name": "🇩🇪 Германия - Франкфурт", "ping": 35, "load": 32, "flag": "de", "type": "preset"},
            {"name": "🇬🇧 Великобритания - Лондон", "ping": 42, "load": 28, "flag": "gb", "type": "preset"},
        ]
        
    def create_ui(self):
        # Создаем основной контейнер с градиентом
        self.main_container = ctk.CTkFrame(self.app, fg_color=self.colors["dark_bg"])
        self.main_container.pack(fill="both", expand=True)
        
        # Создаем layout с sidebar и main content
        self.create_sidebar()
        self.create_main_content()
        
    def create_sidebar(self):
        # Боковая панель
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=280,
            corner_radius=0,
            fg_color=("#2d2d2d", "#1a1a1a")
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Логотип в sidebar
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(30, 20), padx=20)
        
        self.logo_label = ctk.CTkLabel(
            logo_frame,
            text="🛡️ KingzVPN",
            font=("Arial", 22, "bold"),
            text_color=self.colors["primary"]
        )
        self.logo_label.pack()
        
        # Навигация
        self.create_navigation()
        
        # Статус подключения в sidebar
        self.create_sidebar_status()
        
    def create_navigation(self):
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15)
        
        # Кнопки навигации
        nav_buttons = [
            ("🌐 Быстрое подключение", self.show_quick_connect),
            ("📁 Мои конфигурации", self.show_configs),
            ("⚡ Скорость", self.show_speed),
            ("⚙️ Настройки", self.show_settings)
        ]
        
        self.nav_buttons = {}
        for text, command in nav_buttons:
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                font=("Arial", 14),
                height=45,
                fg_color="transparent",
                text_color=("gray70", "gray70"),
                hover_color=("gray60", "gray30"),
                anchor="w",
                command=command
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[text] = btn
        
        # Активируем первую вкладку
        self.show_quick_connect()
        
    def create_sidebar_status(self):
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=15, pady=20)
        
        # Индикатор статуса
        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="● ОФФЛАЙН",
            font=("Arial", 12, "bold"),
            text_color=self.colors["danger"]
        )
        self.status_indicator.pack(anchor="w")
        
        # IP адрес
        self.ip_label = ctk.CTkLabel(
            status_frame,
            text="IP: Загрузка...",
            font=("Arial", 10),
            text_color="gray"
        )
        self.ip_label.pack(anchor="w")
        
        # Загружаем IP в отдельном потоке
        threading.Thread(target=self.load_ip_info, daemon=True).start()
        
    def create_main_content(self):
        # Основная область контента
        self.main_content = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Создаем разные вкладки
        self.create_quick_connect_tab()
        self.create_configs_tab()
        self.create_speed_tab()
        self.create_settings_tab()
        
        # Сначала показываем быструю вкладку
        self.show_quick_connect()
        
    def create_quick_connect_tab(self):
        self.quick_connect_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        
        # Заголовок
        title = ctk.CTkLabel(
            self.quick_connect_frame,
            text="🌐 Быстрое подключение",
            font=("Arial", 28, "bold")
        )
        title.pack(anchor="w", pady=(0, 30))
        
        # Карточка статуса подключения
        self.create_connection_card()
        
        # Предустановленные серверы
        self.create_preset_servers()
        
        # Импорт конфигурации
        self.create_import_section()
        
    def create_connection_card(self):
        connection_card = ctk.CTkFrame(
            self.quick_connect_frame,
            corner_radius=20,
            fg_color=self.colors["card_bg"]
        )
        connection_card.pack(fill="x", pady=(0, 30))
        
        content_frame = ctk.CTkFrame(connection_card, fg_color="transparent")
        content_frame.pack(fill="x", padx=30, pady=30)
        
        # Статус и кнопка подключения
        status_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        status_frame.pack(fill="x")
        
        self.connection_status = ctk.CTkLabel(
            status_frame,
            text="Готов к подключению",
            font=("Arial", 18),
            text_color="gray"
        )
        self.connection_status.pack(side="left")
        
        self.connect_button = ctk.CTkButton(
            status_frame,
            text="ПОДКЛЮЧИТЬСЯ",
            font=("Arial", 16, "bold"),
            height=50,
            width=200,
            fg_color=self.colors["primary"],
            hover_color="#1f6b4a",
            command=self.toggle_connection
        )
        self.connect_button.pack(side="right")
        
        # Прогресс бар
        self.progress_bar = ctk.CTkProgressBar(
            content_frame,
            height=6,
            progress_color=self.colors["success"]
        )
        self.progress_bar.pack(fill="x", pady=(20, 0))
        self.progress_bar.set(0)
        
    def create_preset_servers(self):
        servers_frame = ctk.CTkFrame(self.quick_connect_frame, fg_color="transparent")
        servers_frame.pack(fill="x", pady=(0, 30))
        
        title = ctk.CTkLabel(
            servers_frame,
            text="🚀 Рекомендованные серверы",
            font=("Arial", 20, "bold")
        )
        title.pack(anchor="w", pady=(0, 15))
        
        # Сетка серверов
        grid_frame = ctk.CTkFrame(servers_frame, fg_color="transparent")
        grid_frame.pack(fill="x")
        
        for i, server in enumerate(self.preset_servers):
            server_card = self.create_server_card(server)
            server_card.pack(side="left", fill="x", expand=True, padx=5)
            
    def create_server_card(self, server):
        card = ctk.CTkFrame(
            self.quick_connect_frame,
            corner_radius=15,
            fg_color=self.colors["card_bg"],
            border_width=2,
            border_color=("gray50", "gray30")
        )
        
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Флаг и название
        name_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        name_frame.pack(fill="x")
        
        ctk.CTkLabel(
            name_frame,
            text=server["name"],
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        # Статистика
        stats_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(
            stats_frame,
            text=f"🏓 {server['ping']}ms",
            font=("Arial", 11),
            text_color="#888"
        ).pack(side="left")
        
        ctk.CTkLabel(
            stats_frame,
            text=f"📊 {server['load']}%",
            font=("Arial", 11),
            text_color="#888"
        ).pack(side="left", padx=(10, 0))
        
        # Кнопка подключения
        connect_btn = ctk.CTkButton(
            content_frame,
            text="Подключиться",
            height=35,
            fg_color=self.colors["primary"],
            command=lambda s=server: self.connect_to_preset(s)
        )
        connect_btn.pack(fill="x", pady=(15, 0))
        
        return card
        
    def create_import_section(self):
        import_card = ctk.CTkFrame(
            self.quick_connect_frame,
            corner_radius=20,
            fg_color=self.colors["card_bg"]
        )
        import_card.pack(fill="x")
        
        content_frame = ctk.CTkFrame(import_card, fg_color="transparent")
        content_frame.pack(fill="x", padx=30, pady=25)
        
        title = ctk.CTkLabel(
            content_frame,
            text="📥 Импорт конфигурации",
            font=("Arial", 18, "bold")
        )
        title.pack(anchor="w", pady=(0, 15))
        
        # URL ввод
        url_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        url_frame.pack(fill="x")
        
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Введите URL конфигурации...",
            height=45,
            font=("Arial", 13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Автозаполнение тестовым конфигом
        self.url_entry.insert(0, "http://185.184.123.133:2096/sub/cnk3x4buk8azncdw")
        
        import_btn = ctk.CTkButton(
            url_frame,
            text="Импорт",
            height=45,
            width=120,
            fg_color=self.colors["secondary"],
            command=self.import_config
        )
        import_btn.pack(side="right")
        
    def create_configs_tab(self):
        self.configs_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        
        title = ctk.CTkLabel(
            self.configs_frame,
            text="📁 Мои конфигурации", 
            font=("Arial", 28, "bold")
        )
        title.pack(anchor="w", pady=(0, 30))
        
        # Список конфигураций
        self.configs_scrollable = ctk.CTkScrollableFrame(
            self.configs_frame,
            fg_color="transparent"
        )
        self.configs_scrollable.pack(fill="both", expand=True)
        
    def create_speed_tab(self):
        self.speed_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        
        title = ctk.CTkLabel(
            self.speed_frame,
            text="⚡ Скорость подключения",
            font=("Arial", 28, "bold")
        )
        title.pack(anchor="w", pady=(0, 30))
        
        # Карточки скорости
        speed_cards_frame = ctk.CTkFrame(self.speed_frame, fg_color="transparent")
        speed_cards_frame.pack(fill="x", pady=(0, 30))
        
        self.download_card = self.create_speed_card("📥 Скачать", "0", "Mbps")
        self.download_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.upload_card = self.create_speed_card("📤 Загрузить", "0", "Mbps") 
        self.upload_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.ping_card = self.create_speed_card("🏓 Пинг", "0", "ms")
        self.ping_card.pack(side="left", fill="x", expand=True, padx=5)
        
        # Кнопка теста скорости
        test_btn = ctk.CTkButton(
            self.speed_frame,
            text="Запустить тест скорости",
            height=50,
            font=("Arial", 16, "bold"),
            fg_color=self.colors["primary"],
            command=self.start_speed_test
        )
        test_btn.pack(pady=20)
        
    def create_speed_card(self, title: str, value: str, unit: str) -> ctk.CTkFrame:
        """Создает карточку для отображения скорости с защитой от ошибок"""
        try:
            card = ctk.CTkFrame(
                self.speed_frame,
                corner_radius=15,
                fg_color=self.colors["card_bg"],
                height=150
            )
            card.pack_propagate(False)
            
            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Заголовок
            ctk.CTkLabel(
                content_frame,
                text=title,
                font=("Arial", 16),
                text_color="gray"
            ).pack(anchor="w")
            
            # Значение
            value_label = ctk.CTkLabel(
                content_frame,
                text=value,
                font=("Arial", 32, "bold")
            )
            value_label.pack(expand=True)
            
            # Единица измерения
            ctk.CTkLabel(
                content_frame,
                text=unit,
                font=("Arial", 14),
                text_color="gray"
            ).pack(anchor="e")

            # Сохраняем ссылки на виджеты в словаре
            widget_map = {
                "📥 Скачать": "download",
                "📤 Загрузить": "upload",
                "🏓 Пинг": "ping"
            }
            
            if title in widget_map:
                self.speed_widgets[widget_map[title]] = value_label
                
            return card
            
        except Exception as e:
            self.logger.error(f"Failed to create speed card: {e}")
            # Возвращаем пустой фрейм в случае ошибки
            return ctk.CTkFrame(self.speed_frame, fg_color="transparent")
            
    def safe_destroy(self, widget: Any) -> None:
        """Безопасно удаляет виджет из любого потока"""
        try:
            if widget and widget.winfo_exists():
                widget.destroy()
        except Exception as e:
            self.logger.error(f"Failed to destroy widget: {e}")
        
        return card
        
    def setup_logging(self):
        """Настраивает логирование в файл и консоль с ротацией"""
        try:
            self.logger = logging.getLogger('KingzVPN')
            self.logger.setLevel(logging.DEBUG)
            
            # Форматтер с подробной информацией
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Хендлер для файла с ротацией (10 файлов по 5MB)
            log_file = os.path.join(LOG_DIR, 'vpn.log')
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=5*1024*1024,  # 5MB
                backupCount=10,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            
            # Хендлер для консоли (только важные сообщения)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            
            # Очищаем существующие хендлеры
            self.logger.handlers.clear()
            
            # Добавляем новые хендлеры
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
            self.logger.info("Logging initialized")
            self.logger.debug(f"Python version: {sys.version}")
            self.logger.debug(f"OS: {os.name}")
            self.logger.debug(f"Working directory: {os.getcwd()}")
            
        except Exception as e:
            print(f"Failed to setup logging: {e}")
            self.logger = logging.getLogger('KingzVPN')
            self.logger.addHandler(logging.StreamHandler())
            
    def safe_ui_update(self, widget: Any, **kwargs) -> None:
        """Безопасно обновляет виджеты из любого потока"""
        try:
            self.app.after(0, widget.configure, kwargs)
        except Exception as e:
            self.logger.error(f"UI update failed for {widget}: {e}")
            
    def show_notification(self, message: str, type_: str = "info", duration: int = 3000) -> None:
        """Показывает уведомление с защитой от ошибок"""
        try:
            # Получаем цвет из словаря или используем default
            colors = {
                "success": self.colors["success"],
                "error": self.colors["danger"],
                "warning": self.colors["warning"],
                "info": self.colors["secondary"]
            }
            bg_color = colors.get(type_, self.colors["secondary"])
            
            # Создаем и размещаем уведомление
            notification = ctk.CTkFrame(
                self.app,
                corner_radius=10,
                fg_color=bg_color
            )
            
            # Используем после создания для избежания исключений
            try:
                notification.place(relx=0.5, rely=0.1, anchor="center")
                
                label = ctk.CTkLabel(
                    notification,
                    text=message,
                    text_color="white",
                    font=("Arial", 12)
                )
                label.pack(padx=20, pady=10)
                
                # Логируем уведомление
                log_level = {
                    "success": logging.INFO,
                    "error": logging.ERROR,
                    "warning": logging.WARNING,
                    "info": logging.INFO
                }.get(type_, logging.INFO)
                
                self.logger.log(log_level, f"Notification: {message}")
                
                # Планируем удаление
                self.app.after(duration, notification.destroy)
                
            except Exception as e:
                self.logger.error(f"Failed to show notification content: {e}")
                notification.destroy()
                
        except Exception as e:
            self.logger.error(f"Failed to create notification: {e}")
            print(f"Notification failed: {message} ({e})")
        
    def prepare_vpn_config(self, config):
        """Подготавливает конфиг для OpenVPN"""
        if config['type'] in ['vmess', 'ss', 'trojan']:
            self.log("⚠️ Протокол не поддерживается напрямую. Требуется конвертация.")
            return None
            
        if config['type'] == 'openvpn':
            # Сохраняем .ovpn файл
            config_name = f"config_{int(time.time())}.ovpn"
            config_path = os.path.join(self.openvpn_config_path, config_name)
            
            try:
                with open(config_path, 'w') as f:
                    f.write(config['content'])
                self.log(f"✅ Конфиг сохранен: {config_path}")
                return config_path
            except Exception as e:
                self.log(f"❌ Ошибка сохранения конфига: {e}")
                return None
        
        return None
        
    def monitor_vpn_process(self, process):
        """Мониторит вывод процесса OpenVPN"""
        while process.poll() is None:
            try:
                line = process.stdout.readline()
                if not line:
                    break
                    
                line = line.decode('utf-8', errors='ignore').strip()
                self.process_output.append(line)
                
                # Логируем важные сообщения
                if any(x in line.lower() for x in ['error', 'fatal', 'warn']):
                    self.logger.warning(line)
                    self.app.after(0, self.show_notification, f"VPN: {line}", "warning")
                elif 'initialization sequence completed' in line.lower():
                    self.logger.info("VPN подключение установлено")
                    self.app.after(0, self.connection_success)
                
            except Exception as e:
                self.logger.error(f"Ошибка чтения вывода процесса: {e}")
                
        # Если процесс завершился
        if process.poll() is not None:
            self.logger.warning(f"Процесс OpenVPN завершился с кодом {process.returncode}")
            self.app.after(0, self.handle_connection_error, f"Процесс завершился с кодом {process.returncode}")
            
    def handle_connection_error(self, error_msg):
        """Обрабатывает ошибки подключения"""
        self.logger.error(f"Ошибка подключения: {error_msg}")
        self.disconnect_vpn()
        self.show_notification(f"Ошибка: {error_msg}", "error")
        
    def create_settings_tab(self):
        self.settings_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        
        title = ctk.CTkLabel(
            self.settings_frame,
            text="⚙️ Настройки",
            font=("Arial", 28, "bold")
        )
        title.pack(anchor="w", pady=(0, 30))
        
        # Настройки карточка
        settings_card = ctk.CTkFrame(
            self.settings_frame,
            corner_radius=20,
            fg_color=self.colors["card_bg"]
        )
        settings_card.pack(fill="x")
        
        content_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        content_frame.pack(fill="x", padx=30, pady=25)
        
        # Автозапуск
        auto_start_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        auto_start_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            auto_start_frame,
            text="Запуск с Windows",
            font=("Arial", 14)
        ).pack(side="left")
        
        auto_start_switch = ctk.CTkSwitch(
            auto_start_frame,
            text="",
            width=20
        )
        auto_start_switch.pack(side="right")
        
        # Kill Switch
        kill_switch_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        kill_switch_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            kill_switch_frame,
            text="Kill Switch (блокировка без VPN)",
            font=("Arial", 14)
        ).pack(side="left")
        
        kill_switch = ctk.CTkSwitch(
            kill_switch_frame,
            text="",
            width=20
        )
        kill_switch.pack(side="right")
        
    def show_quick_connect(self):
        self.hide_all_tabs()
        self.quick_connect_frame.pack(fill="both", expand=True)
        self.highlight_nav_button("🌐 Быстрое подключение")
        
    def show_configs(self):
        self.hide_all_tabs()
        self.configs_frame.pack(fill="both", expand=True)
        self.highlight_nav_button("📁 Мои конфигурации")
        
    def show_speed(self):
        self.hide_all_tabs()
        self.speed_frame.pack(fill="both", expand=True)
        self.highlight_nav_button("⚡ Скорость")
        
    def show_settings(self):
        self.hide_all_tabs()
        self.settings_frame.pack(fill="both", expand=True)
        self.highlight_nav_button("⚙️ Настройки")
        
    def hide_all_tabs(self):
        for frame in [self.quick_connect_frame, self.configs_frame, 
                     self.speed_frame, self.settings_frame]:
            frame.pack_forget()
            
    def highlight_nav_button(self, button_text):
        for text, btn in self.nav_buttons.items():
            if text == button_text:
                btn.configure(fg_color=("gray60", "gray30"))
            else:
                btn.configure(fg_color="transparent")
                
    def connect_to_preset(self, server):
        self.log(f"Подключение к {server['name']}...")
        # Здесь будет логика подключения к preset серверам
        
    def import_config(self):
        """Импортирует конфигурацию из URL"""
        try:
            url = self.url_entry.get().strip()
            if not url:
                self.show_notification("Введите URL конфигурации", "warning")
                return
                
            # Базовая валидация URL
            if not url.startswith(('http://', 'https://')):
                self.show_notification("Неверный формат URL", "warning")
                return
                
            # Блокируем UI на время загрузки
            self.url_entry.configure(state="disabled")
            self.show_notification("Загрузка конфигурации...", "info")
            
            # Сохраняем URL для потока
            thread_url = url  # Локальная копия для потока
            
            # Запускаем загрузку в отдельном потоке
            thread = threading.Thread(
                target=self.download_config,
                args=(thread_url,),
                daemon=True
            )
            thread.start()
            
            # Наблюдаем за потоком
            self.active_threads['download'] = thread
            
        except Exception as e:
            self.logger.error(f"Ошибка импорта: {e}")
            self.show_notification(f"Ошибка: {str(e)}", "error")
            self.url_entry.configure(state="normal")
        
    def download_config(self, url: str) -> None:
        """Загружает и анализирует конфигурацию VPN безопасно"""
        if not isinstance(url, str):
            self.app.after(0, self.show_notification, "Неверный формат URL", "error")
            return

        try:
            self.logger.info(f"Загрузка конфига с URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/plain, application/json, application/x-ovpn',
                'Connection': 'close'
            }
            
            # Отключаем предупреждения о SSL для некоторых VPN сервисов
            with urllib3.disable_warnings():
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=30, 
                    verify=False, 
                    stream=True
                )
                response.raise_for_status()
                
                # Ограничиваем размер ответа
                content = ""
                total_size = 0
                chunk_size = 8192
                max_size = 1024 * 1024  # 1MB limit
                
                for chunk in response.iter_content(chunk_size=chunk_size, decode_unicode=True):
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise ValueError("Размер конфига превышает 1MB")
                    content += chunk
                
            content = content.strip()
            self.logger.info(f"Получено {len(content)} байт")
            
            # Анализируем содержимое
            if len(content) > 50000:
                self.logger.warning("Большой размер конфига, обрезаем до 50KB")
                content = content[:50000]
            
            config_type = self.detect_config_type(content)
            if not config_type:
                raise ValueError("Неизвестный формат конфигурации")
                
            config_data = {
                'name': f"{config_type} {time.strftime('%H:%M')}",
                'type': config_type,
                'content': content,
                'url': url,
                'imported_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.logger.info(f"Конфиг определен как: {config_type}")
            self.app.after(0, self.add_config, config_data)
            self.app.after(0, lambda: self.show_notification(f"Конфигурация {config_type} загружена!", "success"))
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка сети: {str(e)}"
            self.logger.error(error_msg)
            self.app.after(0, lambda: self.show_notification(error_msg, "error"))
        except Exception as e:
            error_msg = f"Ошибка обработки: {str(e)}"
            self.logger.error(error_msg)
            self.app.after(0, lambda: self.show_notification(error_msg, "error"))
            
    def detect_config_type(self, content: str, max_recursion: int = 3) -> Optional[str]:
        """
        Определяет тип конфигурации по содержимому с защитой от рекурсии
        
        Args:
            content: Содержимое конфига
            max_recursion: Максимальная глубина рекурсии для декодирования base64
            
        Returns:
            Тип конфига или None если не удалось определить
        """
        if not content or max_recursion <= 0:
            return None
            
        content = content.strip()
        
        # OpenVPN конфиг (более строгая проверка)
        if all(x in content.lower() for x in ['client', 'remote']) and \
           any(x in content.lower() for x in ['proto tcp', 'proto udp']):
            return 'openvpn'
            
        # VMess с проверкой структуры
        if 'vmess://' in content:
            try:
                vmess_data = content.split('vmess://')[1].strip()
                decoded = base64.b64decode(vmess_data + '=' * (-len(vmess_data) % 4))
                config = json.loads(decoded)
                required = ['add', 'port', 'id', 'aid']  # Минимальные обязательные поля
                if all(x in config for x in required):
                    return 'vmess'
            except Exception as e:
                self.logger.debug(f"VMess validation failed: {e}")
            
        # ShadowSocks с валидацией
        if 'ss://' in content:
            try:
                ss_url = re.search(r'ss://([^#\s]+)', content).group(1)
                # Проверяем base64 часть
                if '#' in ss_url:
                    ss_url = ss_url.split('#')[0]
                decoded = base64.b64decode(ss_url + '=' * (-len(ss_url) % 4))
                if b':' in decoded and b'@' in decoded:  # Проверяем формат method:password@host:port
                    return 'shadowsocks'
            except Exception as e:
                self.logger.debug(f"SS validation failed: {e}")
            
        # Trojan с проверкой формата
        if 'trojan://' in content:
            try:
                if re.match(r'trojan://[^@]+@[\w\-\.]+:\d+\??[^#]*(?:#.*)?$', content):
                    return 'trojan'
            except Exception as e:
                self.logger.debug(f"Trojan validation failed: {e}")
            
        # Base64 с рекурсией и лимитом
        try:
            if re.match(r'^[A-Za-z0-9+/=]+$', content):
                missing_padding = (-len(content) % 4)
                if missing_padding:
                    content += '=' * missing_padding
                    
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                # Проверяем размер декодированного содержимого
                if len(decoded) > 50000:
                    self.logger.warning("Base64 decoded content too large, truncating")
                    decoded = decoded[:50000]
                    
                if any(x in decoded for x in ['client', 'vmess://', 'ss://', 'trojan://']):
                    # Рекурсивный вызов с уменьшением счетчика
                    return self.detect_config_type(decoded, max_recursion - 1)
        except Exception as e:
            self.logger.debug(f"Base64 decode failed: {e}")
            
        # JSON/YAML с конфигами (более тщательная проверка)
        try:
            if content.lstrip().startswith(('{', '[')):
                data = json.loads(content)
                
                # Проверяем разные форматы
                if isinstance(data, dict):
                    # Clash формат
                    if 'proxies' in data and isinstance(data['proxies'], list):
                        return 'clash_config'
                    # Обычный JSON конфиг
                    if any(x in data for x in ['server', 'remote', 'address']):
                        return 'json_config'
                elif isinstance(data, list):
                    # Массив конфигов
                    if any(isinstance(x, dict) and 'type' in x for x in data):
                        return 'json_config'
                        
        except json.JSONDecodeError:
            self.logger.debug("Not a valid JSON")
        except Exception as e:
            self.logger.debug(f"JSON validation failed: {e}")
            
        return None
            
    def add_config(self, config_data):
        """Добавляет новую конфигурацию"""
        try:
            # Подготавливаем конфиг перед сохранением
            config_data = self.prepare_config_data(config_data)
            if not config_data:
                raise ValueError("Неверный формат конфигурации")
                
            # Сохраняем в файл если это OpenVPN конфиг
            if config_data['type'] == 'openvpn':
                config_path = self.save_openvpn_config(config_data)
                if config_path:
                    config_data['file_path'] = config_path
                    
            # Проверяем на дубликаты
            for existing in self.configs:
                if self.is_duplicate_config(existing, config_data):
                    self.logger.warning("Обнаружен дубликат конфига")
                    self.show_notification("Такой конфиг уже добавлен", "warning")
                    return
                    
            self.configs.append(config_data)
            self.create_config_card(config_data)
            self.logger.info(f"Добавлен конфиг: {config_data['name']}")
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления конфига: {e}")
            self.show_notification(f"Ошибка: {str(e)}", "error")
            
    def is_duplicate_config(self, config1, config2):
        """Проверяет, являются ли конфиги дубликатами"""
        if config1['type'] != config2['type']:
            return False
            
        if config1.get('url') and config2.get('url'):
            return config1['url'] == config2['url']
            
        if 'content' in config1 and 'content' in config2:
            return config1['content'] == config2['content']
            
        return False
        
    def prepare_config_data(self, config_data):
        """Подготавливает и валидирует данные конфига"""
        required_fields = ['name', 'type', 'content']
        for field in required_fields:
            if field not in config_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
                
        # Нормализуем тип
        config_data['type'] = config_data['type'].lower()
        
        # Добавляем метку времени если нет
        if 'imported_at' not in config_data:
            config_data['imported_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
            
        return config_data
        
    def save_openvpn_config(self, config_data):
        """Сохраняет OpenVPN конфиг в файл"""
        try:
            if not os.path.exists(self.openvpn_config_path):
                os.makedirs(self.openvpn_config_path)
                
            safe_name = re.sub(r'[^\w\-_.]', '_', config_data['name'])
            config_path = os.path.join(
                self.openvpn_config_path,
                f"{safe_name}_{int(time.time())}.ovpn"
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_data['content'])
                
            self.logger.info(f"Сохранен конфиг: {config_path}")
            return config_path
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения конфига: {e}")
            return None
            
    def validate_config_content(self, config_data):
        """Проверяет содержимое конфига на валидность"""
        try:
            config_type = config_data.get('type', '').lower()
            content = config_data.get('content', '')
            
            if not content:
                return False
                
            if config_type == 'openvpn':
                # Проверяем основные директивы OpenVPN
                required = ['client', 'remote', 'proto']
                return all(x in content.lower() for x in required)
                
            elif config_type == 'vmess':
                # Для VMess проверяем JSON структуру
                if 'vmess://' in content:
                    vmess_data = content.split('vmess://')[1]
                    try:
                        decoded = base64.b64decode(vmess_data + '=' * (-len(vmess_data) % 4))
                        json.loads(decoded)
                        return True
                    except:
                        return False
                        
            elif config_type == 'shadowsocks':
                # Проверяем формат SS URL
                return bool(re.match(r'ss://[A-Za-z0-9+/=]+@[\w\-\.]+:\d+', content))
                
            elif config_type == 'trojan':
                # Проверяем формат Trojan URL
                return bool(re.match(r'trojan://[^@]+@[\w\-\.]+:\d+', content))
                
            elif config_type == 'json_config':
                # Проверяем что это валидный JSON
                try:
                    json.loads(content)
                    return True
                except:
                    return False
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации конфига: {e}")
            return False
            
    def create_config_card(self, config):
        """Создает карточку конфигурации в UI"""
        card = ctk.CTkFrame(
            self.configs_scrollable,
            corner_radius=15,
            fg_color=self.colors["card_bg"]
        )
        card.pack(fill="x", pady=5, padx=5)
        
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=15)
        
        # Информация о конфиге
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(
            info_frame,
            text=config['name'],
            font=("Arial", 14, "bold")
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            info_frame,
            text=f"Тип: {config['type']} • {config['imported_at']}",
            font=("Arial", 11),
            text_color="gray"
        ).pack(anchor="w", pady=(2, 0))
        
        # Кнопки действий
        actions_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        actions_frame.pack(side="right")
        
        ctk.CTkButton(
            actions_frame,
            text="Подключить",
            width=100,
            fg_color=self.colors["primary"],
            command=lambda c=config: self.connect_to_config(c)
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            actions_frame,
            text="Удалить",
            width=100,
            fg_color=self.colors["danger"],
            command=lambda c=config, card=card: self.delete_config(c, card)
        ).pack(side="left")
        
    def connect_to_config(self, config):
        self.current_config = config
        self.connect_vpn()
        
    def check_openvpn_installed(self) -> bool:
        """Проверяет наличие OpenVPN в системе"""
        try:
            result = subprocess_check_output(['openvpn', '--version'], 
                                          stderr=STDOUT, timeout=2).decode()
            self.logger.info(f"OpenVPN version: {result.splitlines()[0]}")
            return True
        except Exception as e:
            self.logger.error(f"OpenVPN not found: {e}")
            return False
            
    def cleanup_old_configs(self, max_age_days: int = 7) -> None:
        """Удаляет старые конфиги"""
        try:
            now = time.time()
            for root, _, files in os.walk(CONFIG_DIR):
                for f in files:
                    if not f.endswith('.ovpn'):
                        continue
                    fpath = os.path.join(root, f)
                    if now - os.path.getmtime(fpath) > max_age_days * 86400:
                        try:
                            os.remove(fpath)
                            self.logger.info(f"Removed old config: {f}")
                        except OSError as e:
                            self.logger.error(f"Failed to remove {f}: {e}")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            
    def connect_vpn(self):
        """Инициирует подключение к VPN"""
        if not self.current_config:
            self.show_notification("Выберите конфигурацию", "warning")
            return
            
        # Проверка OpenVPN
        if not self.check_openvpn_installed():
            self.show_notification("OpenVPN не установлен!", "error")
            return
            
        # Защита от множественных попыток подключения
        if not self.connection_lock.acquire(blocking=False):
            self.logger.warning("Подключение уже в процессе")
            self.show_notification("Подключение уже выполняется", "warning")
            return
            
        # Очистка старых конфигов при подключении
        self.cleanup_old_configs()
            
        try:
            if self.is_connected:
                self.disconnect_vpn()
                return
                
            self.is_connected = True
            self.connect_button.configure(
                text="ОТКЛЮЧИТЬСЯ",
                fg_color=self.colors["danger"],
                hover_color="#ff5252",
                state="disabled"  # Блокируем на время подключения
            )
            
            self.connection_status.configure(
                text="Подключение...",
                text_color=self.colors["warning"]
            )
            
            self.status_indicator.configure(
                text="● ПОДКЛЮЧЕНИЕ...",
                text_color=self.colors["warning"]
            )
            
            self.progress_bar.start()
            
            # Подготавливаем конфиг
            config_path = self.prepare_vpn_config(self.current_config)
            if not config_path:
                raise Exception("Не удалось подготовить конфигурацию")
                
            # Запускаем OpenVPN
            cmd = [
                'openvpn',  # Предполагается что OpenVPN установлен и доступен в PATH
                '--config', config_path,
                '--auth-nocache'  # Не кэшировать пароли
            ]
            
            self.logger.info(f"Запуск OpenVPN: {' '.join(cmd)}")
            
            process = Popen(
                cmd,
                stdout=PIPE,
                stderr=STDOUT,
                bufsize=1,
                universal_newlines=False
            )
            
            self.vpn_process = process
            
            # Запускаем мониторинг процесса в отдельном потоке
            monitor_thread = threading.Thread(
                target=self.monitor_vpn_process,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Сохраняем поток для возможности остановки
            self.active_threads['process'] = monitor_thread
            
            # Запускаем мониторинг статистики
            self.stats_stop_event.clear()  # Сбрасываем event остановки
            stats_thread = threading.Thread(target=self.start_stats_monitor, daemon=True)
            stats_thread.start()
            self.active_threads['stats'] = stats_thread
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения: {e}")
            self.show_notification(f"Ошибка: {str(e)}", "error")
            self.disconnect_vpn()
        finally:
            self.connect_button.configure(state="normal")
            self.connection_lock.release()
        
    def disconnect_vpn(self):
        """Отключает VPN соединение с корректной очисткой ресурсов"""
        self.logger.info("Отключение VPN...")
        
        # Останавливаем все мониторинги
        for event_name in self.events:
            self.events[event_name].set()
        
        # Останавливаем процесс OpenVPN если он запущен
        if self.vpn_process:
            try:
                self.vpn_process.terminate()
                try:
                    self.vpn_process.wait(timeout=5)
                except TimeoutExpired:
                    self.logger.warning("OpenVPN process not responding, forcing kill")
                    self.vpn_process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping OpenVPN process: {e}")
            finally:
                self.vpn_process = None
                
        # Останавливаем все активные потоки
        for thread_name, thread in self.active_threads.items():
            if thread and thread.is_alive():
                self.logger.info(f"Waiting for thread {thread_name} to finish")
                try:
                    thread.join(timeout=2)
                    if thread.is_alive():
                        self.logger.warning(f"Thread {thread_name} did not finish in time")
                except Exception as e:
                    self.logger.error(f"Error joining thread {thread_name}: {e}")
                
        # Очищаем все потоки
        self.active_threads = {k: None for k in self.active_threads}
        
        # Очищаем очередь статистики
        try:
            while not self.stats_queue.empty():
                self.stats_queue.get_nowait()
        except Exception as e:
            self.logger.error(f"Error clearing stats queue: {e}")
            
        self.is_connected = False
        
        # Безопасно обновляем UI
        self.safe_ui_update(
            self.connect_button,
            text="ПОДКЛЮЧИТЬСЯ",
            fg_color=self.colors["primary"],
            hover_color="#1f6b4a"
        )
        
        self.safe_ui_update(
            self.connection_status,
            text="Отключено",
            text_color="gray"
        )
        
        self.safe_ui_update(
            self.status_indicator,
            text="● ОФФЛАЙН", 
            text_color=self.colors["danger"]
        )
        
        # Сбрасываем прогресс
        self.progress_bar.stop()
        self.progress_bar.set(0)
        
        # Сбрасываем статистику безопасно
        for widget in self.speed_widgets.values():
            if widget and widget.winfo_exists():
                self.safe_ui_update(widget, text="0")
        
        self.show_notification("VPN отключен", "info")
        self.logger.info("VPN отключен")
        
    def toggle_connection(self):
        """Переключает состояние подключения"""
        if not self.is_connected:
            self.connect_vpn()
        else:
            self.disconnect_vpn()
            
    def update_connection_status(self, status, progress=None):
        """Обновляет статус подключения в UI"""
        self.connection_status.configure(text=status)
        if progress is not None:
            self.progress_bar.set(progress)
        
    def connection_success(self):
        """Обрабатывает успешное подключение"""
        self.logger.info("VPN подключение установлено")
        
        self.connection_status.configure(
            text="Защищено ✓",
            text_color=self.colors["success"]
        )
        
        self.status_indicator.configure(
            text="● ОНЛАЙН",
            text_color=self.colors["success"] 
        )
        
        self.progress_bar.set(1.0)
        self.progress_bar.stop()
        
        self.show_notification("VPN успешно подключен!", "success")
        
    def start_stats_monitor(self) -> None:
        """Запускает мониторинг сетевой статистики с защитой от ошибок"""
        self.logger.info("Запуск мониторинга статистики")
        
        try:
            # Получаем начальные значения счетчиков
            net_io = psutil.net_io_counters()
            last_bytes = {
                'sent': net_io.bytes_sent,
                'recv': net_io.bytes_recv
            }
            last_time = time.time()
            
            while not self.events['stats_stop'].is_set():
                try:
                    current_time = time.time()
                    interval = max(current_time - last_time, 0.1)  # Защита от деления на 0
                    
                    # Получаем текущие значения с защитой от ошибок
                    try:
                        counters = psutil.net_io_counters()
                        current_bytes = {
                            'sent': counters.bytes_sent,
                            'recv': counters.bytes_recv
                        }
                    except Exception as e:
                        self.logger.error(f"Failed to get network counters: {e}")
                        time.sleep(1)
                        continue
                    
                    # Считаем скорость с проверкой переполнения
                    speeds = {}
                    for direction in ['sent', 'recv']:
                        byte_diff = current_bytes[direction] - last_bytes[direction]
                        if byte_diff < 0:  # Counter overflow
                            byte_diff = current_bytes[direction]
                        speeds[direction] = (byte_diff * 8) / (1024 * 1024 * interval)
                    
                    # Измеряем пинг асинхронно
                    ping_ms = self.measure_ping()
                    
                    # Отправляем данные в очередь для обновления UI
                    stats_data = {
                        'download': speeds['recv'],
                        'upload': speeds['sent'],
                        'ping': ping_ms
                    }
                    
                    try:
                        self.stats_queue.put_nowait(stats_data)
                        self.app.after(0, self.process_stats_queue)
                    except Exception as e:
                        self.logger.error(f"Failed to queue stats update: {e}")
                    
                    # Обновляем значения для следующей итерации
                    last_bytes = current_bytes.copy()
                    last_time = current_time
                    
                except Exception as e:
                    self.logger.error(f"Stats monitor iteration error: {e}")
                    
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Stats monitor critical error: {e}")
        finally:
            self.logger.info("Stats monitor stopped")
            
    def measure_ping(self) -> int:
        """Измеряет пинг до Google DNS с защитой от ошибок"""
        try:
            ping_output = subprocess_check_output(
                ['ping', '-n', '1', '8.8.8.8'],
                stderr=STDOUT,
                timeout=2
            ).decode('utf-8', errors='ignore')
            
            match = re.search(r'время=(\d+)мс', ping_output)
            if match:
                return int(match.group(1))
        except Exception as e:
            self.logger.debug(f"Ping measurement failed: {e}")
        return 0
        
    def process_stats_queue(self) -> None:
        """Обрабатывает очередь обновлений статистики"""
        try:
            while not self.stats_queue.empty():
                stats = self.stats_queue.get_nowait()
                if stats:
                    self.update_speed_stats(
                        stats['download'],
                        stats['upload'],
                        stats['ping']
                    )
        except Exception as e:
            self.logger.error(f"Failed to process stats queue: {e}")
            
    def update_speed_stats(self, download: float, upload: float, ping: int) -> None:
        """Thread-safe обновление статистики в UI"""
        try:
            updates = {
                'download': f"{download:.1f}",
                'upload': f"{upload:.1f}",
                'ping': str(ping)
            }
            
            for key, value in updates.items():
                widget = self.speed_widgets.get(key)
                if widget and widget.winfo_exists():
                    self.safe_ui_update(widget, text=value)
                    
        except Exception as e:
            self.logger.error(f"Failed to update speed stats: {e}")
        
    def start_speed_test(self):
        self.show_notification("Запуск теста скорости...", "info")
        # Имитация теста скорости
        threading.Thread(target=self.simulate_speed_test, daemon=True).start()
        
    def simulate_speed_test(self):
        for i in range(101):
            time.sleep(0.03)
            self.app.after(0, self.progress_bar.set, i/100)
            
        time.sleep(1)
        self.app.after(0, self.progress_bar.set, 0)
        self.app.after(0, lambda: self.show_notification("Тест скорости завершен!", "success"))
        
    def load_ip_info(self):
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            ip = response.text
            self.app.after(0, self.ip_label.configure, {"text": f"IP: {ip}"})
        except:
            self.app.after(0, self.ip_label.configure, {"text": "IP: Недоступно"})
            
    def show_notification(self, message: str, type_: str = "info", duration: int = 3000) -> None:
        """Thread-safe метод показа уведомлений с защитой от ошибок"""
        if not isinstance(message, str):
            self.logger.error(f"Invalid notification message type: {type(message)}")
            return
            
        def create_notification():
            try:
                # Создаем временное уведомление
                notification = ctk.CTkFrame(
                    self.app,
                    corner_radius=10,
                    fg_color={
                        "success": self.colors["success"],
                        "error": self.colors["danger"], 
                        "warning": self.colors["warning"],
                        "info": self.colors["secondary"]
                    }.get(type_, self.colors["secondary"])  # Safe default
                )
                
                try:
                    notification.place(relx=0.5, rely=0.1, anchor="center")
                except Exception as e:
                    self.logger.error(f"Failed to place notification: {e}")
                    return
                
                label = ctk.CTkLabel(
                    notification,
                    text=message[:200],  # Ограничиваем длину сообщения
                    text_color="white",
                    font=("Arial", 12)
                )
                label.pack(padx=20, pady=10)
                
                # Логируем уведомление
                log_level = {
                    "success": logging.INFO,
                    "error": logging.ERROR,
                    "warning": logging.WARNING,
                    "info": logging.INFO
                }.get(type_, logging.INFO)
                
                self.logger.log(log_level, f"Notification [{type_}]: {message}")
                
                # Автоскрытие через указанное время
                self.app.after(duration, lambda: self.safe_destroy(notification))
                
            except Exception as e:
                self.logger.error(f"Failed to create notification: {e}")
                
        # Запускаем создание уведомления в основном потоке
        if threading.current_thread() is threading.main_thread():
            create_notification()
        else:
            self.app.after(0, create_notification)
        
    def delete_config(self, config, card):
        self.configs.remove(config)
        card.destroy()
        self.show_notification("Конфигурация удалена", "info")
        
    def log(self, message):
        print(f"[VPN] {message}")
        
    def run(self):
        self.app.mainloop()

# Запуск приложения
if __name__ == "__main__":
    import random  # Добавляем для имитации статистики
    
    vpn_app = ModernVPNClient()
    vpn_app.run()