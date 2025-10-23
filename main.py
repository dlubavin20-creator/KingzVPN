import sys
import os
import subprocess
import importlib
import platform
import time
from pathlib import Path

# ===== IMPROVED DEPENDENCY INSTALLATION SYSTEM =====
class DependencyManager:
    def __init__(self):
        # Updated package list - removed problematic packages
        self.required_packages = {
            'customtkinter': 'customtkinter',
            'requests': 'requests', 
            'urllib3': 'urllib3',
            'psutil': 'psutil',
            'pillow': 'PIL',
            'speedtest-cli': 'speedtest',
            'ping3': 'ping3',
            'python-nmap': 'nmap',
            'pycryptodome': 'Crypto',
            'cryptography': 'cryptography',
            'qrcode': 'qrcode',
            'pyperclip': 'pyperclip',
            'netifaces': 'netifaces',
        }
        
        # Platform-specific packages
        self.windows_packages = {
            'pywin32': 'win32clipboard'
        }
        
        self.optional_packages = {
            'ifaddr': 'ifaddr',
            'scapy': 'scapy',
            'dnspython': 'dns',
            'aiohttp': 'aiohttp',
        }
        
        self.install_log = []
        
    def check_system_requirements(self):
        """Check system compatibility"""
        system = platform.system()
        version = platform.python_version()
        
        print(f"System: {system}")
        print(f"Python: {version}")
        
        if system not in ['Windows', 'Linux', 'Darwin']:
            print("⚠️  Warning: Unsupported operating system")
            
        # Check Python version
        python_version = tuple(map(int, version.split('.')[:2]))
        if python_version < (3, 7):
            print("❌ Error: Python 3.7 or higher required")
            return False
            
        return True
    
    def is_package_installed(self, package_name):
        """Check if package is installed using importlib"""
        try:
            if package_name in self.required_packages:
                import_name = self.required_packages[package_name]
            elif package_name in self.windows_packages:
                import_name = self.windows_packages[package_name]
            elif package_name in self.optional_packages:
                import_name = self.optional_packages[package_name]
            else:
                import_name = package_name
                
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"⚠️  Warning checking {package_name}: {e}")
            return False
    
    def get_install_command(self):
        """Get appropriate pip command - SIMPLIFIED"""
        # Try the most common commands
        commands_to_try = [
            [sys.executable, '-m', 'pip'],
            ['pip3'],
            ['pip']
        ]
        
        for cmd in commands_to_try:
            try:
                # Test if command works
                result = subprocess.run(
                    cmd + ['--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    print(f"✅ Found pip: {' '.join(cmd)}")
                    return cmd
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
                
        print("❌ Could not find pip command")
        return None
    
    def install_package(self, package, upgrade=False, user=False, timeout=120):
        """Install a single package with better error handling"""
        pip_cmd = self.get_install_command()
        if not pip_cmd:
            return False, "Could not find pip"
            
        # Build command
        cmd = pip_cmd + ['install', package]
        if upgrade:
            cmd.append('--upgrade')
        if user:
            cmd.append('--user')
            
        # Add extra flags for better compatibility
        cmd.extend(['--no-warn-script-location', '--quiet'])
            
        try:
            print(f"📦 Installing {package}...")
            
            # Run installation
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            self.install_log.append(f"✅ Success: {package}")
            print(f"   ✅ {package} installed successfully")
            return True, f"Installed {package}"
            
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout installing {package} (>{timeout}s)"
            self.install_log.append(f"❌ {error_msg}")
            print(f"   ❌ {error_msg}")
            return False, error_msg
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install {package}"
            
            # Provide more specific error messages
            if "No matching distribution" in e.stderr:
                error_msg += " - Package not found"
            elif "Permission" in e.stderr:
                error_msg += " - Permission denied"
            elif "Network" in e.stderr or "connect" in e.stderr:
                error_msg += " - Network error"
            else:
                error_msg += f": {e.stderr.strip()[:100]}"
                
            self.install_log.append(f"❌ {error_msg}")
            print(f"   ❌ {error_msg}")
            
            # Try with user flag as fallback (if not already tried)
            if not user and "Permission" in e.stderr:
                print(f"   🔄 Retrying with --user flag...")
                return self.install_package(package, upgrade, user=True, timeout=timeout)
                
            return False, error_msg
    
    def install_all_dependencies(self, upgrade=False, include_optional=False):
        """Install all required dependencies with better logic"""
        print("🚀 Starting dependency installation...")
        print("=" * 50)
        
        # Check pip availability first
        pip_cmd = self.get_install_command()
        if not pip_cmd:
            print("❌ Error: Could not find pip. Please install pip first.")
            return False
            
        # Update pip first (but don't fail if it doesn't work)
        print("🔄 Checking pip version...")
        try:
            subprocess.run(
                pip_cmd + ['install', '--upgrade', 'pip'], 
                capture_output=True, 
                timeout=60
            )
            print("✅ Pip check completed")
        except subprocess.SubprocessError:
            print("⚠️  Could not update pip, continuing...")
        
        # Determine which packages to install
        packages_to_install = []
        
        # Check required packages
        print("\n🔍 Checking required packages...")
        for pkg, import_name in self.required_packages.items():
            if self.is_package_installed(pkg):
                print(f"   ✅ {pkg}")
            else:
                print(f"   ❌ {pkg}")
                packages_to_install.append(pkg)
        
        # Add Windows-specific packages
        if platform.system() == 'Windows':
            print("\n🔍 Checking Windows-specific packages...")
            for pkg, import_name in self.windows_packages.items():
                if self.is_package_installed(pkg):
                    print(f"   ✅ {pkg}")
                else:
                    print(f"   ❌ {pkg}")
                    packages_to_install.append(pkg)
        
        # Add optional packages if requested
        if include_optional:
            print("\n🔍 Checking optional packages...")
            for pkg, import_name in self.optional_packages.items():
                if self.is_package_installed(pkg):
                    print(f"   ✅ {pkg}")
                else:
                    print(f"   ❌ {pkg}")
                    packages_to_install.append(pkg)
        
        if not packages_to_install:
            print("\n🎉 All dependencies are already installed!")
            return True
        
        print(f"\n📦 Packages to install: {len(packages_to_install)}")
        print("=" * 50)
        
        # Install packages with progress
        success_count = 0
        failed_packages = []
        
        for i, package in enumerate(packages_to_install, 1):
            print(f"\n[{i}/{len(packages_to_install)}] Installing {package}...")
            success, message = self.install_package(package, upgrade)
            if success:
                success_count += 1
            else:
                failed_packages.append((package, message))
            
            # Brief pause between installations
            time.sleep(1)
        
        # Print comprehensive summary
        print("\n" + "=" * 50)
        print("📊 INSTALLATION SUMMARY")
        print("=" * 50)
        print(f"✅ Successful: {success_count}/{len(packages_to_install)}")
        print(f"❌ Failed: {len(failed_packages)}")
        
        if failed_packages:
            print("\n❌ Failed packages:")
            for pkg, error in failed_packages:
                print(f"   • {pkg}: {error}")
            
            print("\n💡 Solutions:")
            print("1. Try running as administrator/root")
            print("2. Check internet connection")
            print("3. Try manual installation: pip install package_name")
            print("4. Some packages might not be available for your platform")
            
            # Suggest manual installation commands
            print("\n🔧 Manual installation commands:")
            for pkg, error in failed_packages:
                print(f"   pip install {pkg}")
        
        return len(failed_packages) == 0
    
    def create_requirements_file(self, filename='requirements.txt'):
        """Create requirements.txt file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# KingzVPN Pro - Requirements\n")
                f.write("# Generated automatically\n")
                f.write(f"# Python {platform.python_version()}\n")
                f.write(f"# System: {platform.system()}\n\n")
                
                f.write("# Required packages\n")
                for pkg in self.required_packages.keys():
                    f.write(f"{pkg}\n")
                
                # Add platform-specific packages
                if platform.system() == 'Windows':
                    f.write("\n# Windows-specific packages\n")
                    for pkg in self.windows_packages.keys():
                        f.write(f"{pkg}\n")
                
                f.write("\n# Optional packages\n")
                for pkg in self.optional_packages.keys():
                    f.write(f"#{pkg}\n")
            
            print(f"✅ Requirements file created: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create requirements file: {e}")
            return False

# ===== ENHANCED VPN CLIENT WITH BETTER DEPENDENCY HANDLING =====
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
import tkinter as tk
from tkinter import messagebox
import socket
import platform
import webbrowser
import sqlite3
import hashlib
import secrets
import string
import zipfile
import tempfile
import shutil

# Import available libraries with fallbacks
CRYPTO_AVAILABLE = False
QRCODE_AVAILABLE = False
SPEEDTEST_AVAILABLE = False
PING3_AVAILABLE = False
NETIFACES_AVAILABLE = False
PYPERCLIP_AVAILABLE = False
WIN32CLIPBOARD_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
    print("✅ cryptography available")
except ImportError as e:
    print("❌ cryptography not available")

try:
    import qrcode
    from PIL import Image, ImageTk
    QRCODE_AVAILABLE = True
    print("✅ qrcode available")
except ImportError as e:
    print("❌ qrcode not available")

try:
    import speedtest
    SPEEDTEST_AVAILABLE = True
    print("✅ speedtest available")
except ImportError as e:
    print("❌ speedtest not available")

try:
    import ping3
    PING3_AVAILABLE = True
    print("✅ ping3 available")
except ImportError as e:
    print("❌ ping3 not available")

try:
    import netifaces
    NETIFACES_AVAILABLE = True
    print("✅ netifaces available")
except ImportError as e:
    print("❌ netifaces not available")

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
    print("✅ pyperclip available")
except ImportError as e:
    print("❌ pyperclip not available")

try:
    import win32clipboard
    WIN32CLIPBOARD_AVAILABLE = True
    print("✅ win32clipboard available")
except ImportError as e:
    print("❌ win32clipboard not available")

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup app directories
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(APP_DIR, 'vpn_configs')
LOG_DIR = os.path.join(APP_DIR, 'logs')
DB_DIR = os.path.join(APP_DIR, 'database')
CACHE_DIR = os.path.join(APP_DIR, 'cache')
for d in [CONFIG_DIR, LOG_DIR, DB_DIR, CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

# Configure CTk for better performance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AdvancedVPNClient:
    def __init__(self, auto_install_deps=True):
        print("🚀 Initializing KingzVPN Pro...")
        
        # Initialize dependency manager
        self.dep_manager = DependencyManager()
        
        # Check and install dependencies if needed
        if auto_install_deps:
            self.install_missing_dependencies()
        
        # Now initialize the main application
        self.app = ctk.CTk()
        self.setup_window()
        
        # Initialize all UI frames first
        self.quick_connect_frame = None
        self.configs_frame = None
        self.speed_frame = None
        self.settings_frame = None
        self.tools_frame = None
        self.deps_frame = None
        self.main_content = None
        self.sidebar = None
        
        self.configs = []
        self.current_config = None
        self.vpn_process = None
        self.is_connected = False
        
        self.connection_lock = threading.Lock()
        self.process_output = []
        self.openvpn_config_path = CONFIG_DIR

        # Enhanced events system
        self.events = {
            'stats_stop': Event(),
            'monitor_stop': Event(),
            'process_stop': Event(),
            'scan_stop': Event(),
            'update_stop': Event()
        }
        
        self.active_threads = {}
        self.stats_queue = Queue(maxsize=50)
        
        self.speed_widgets = {}
        self.nav_buttons = {}
        
        # Performance optimization
        self.last_stats_update = 0
        self.stats_update_interval = 0.5
        
        # Enhanced functionality storage
        self.network_devices = []
        self.port_scan_results = []
        self.traffic_data = []
        self.connection_history = []
        self.favorite_servers = []
        self.auto_connect_rules = []
        
        self.setup_logging()
        self.setup_database()
        self.load_user_preferences()
        
        # Enhanced color scheme
        self.colors = {
            "primary": "#2b825b",
            "secondary": "#2196F3", 
            "success": "#4CAF50",
            "warning": "#FF9800",
            "danger": "#ff6b6b",
            "dark_bg": "#1a1a1a",
            "card_bg": "#2d2d2d",
            "text_primary": "#ffffff",
            "text_secondary": "#b0b0b0"
        }
        
        self.load_data()
        self.create_ui()
        
    def install_missing_dependencies(self):
        """Install missing dependencies automatically"""
        print("\n" + "=" * 50)
        print("🔍 Checking dependencies...")
        print("=" * 50)
        
        # First check system requirements
        if not self.dep_manager.check_system_requirements():
            print("❌ System requirements not met")
            response = input("Continue anyway? (y/n): ")
            if response.lower() not in ['y', 'yes']:
                sys.exit(1)
        
        missing_packages = []
        for pkg, import_name in self.dep_manager.required_packages.items():
            if not self.dep_manager.is_package_installed(pkg):
                missing_packages.append(pkg)
        
        # Check Windows packages
        if platform.system() == 'Windows':
            for pkg, import_name in self.dep_manager.windows_packages.items():
                if not self.dep_manager.is_package_installed(pkg):
                    missing_packages.append(pkg)
        
        if missing_packages:
            print(f"❌ Missing {len(missing_packages)} packages: {', '.join(missing_packages)}")
            print("\n💡 Some features may not work without these packages.")
            
            response = input("🤔 Install missing dependencies automatically? (y/n): ")
            
            if response.lower() in ['y', 'yes']:
                print("🚀 Starting automatic installation...")
                success = self.dep_manager.install_all_dependencies()
                
                if success:
                    print("✅ All dependencies installed successfully!")
                    print("🔄 Restarting application to load new dependencies...")
                    time.sleep(2)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    print("❌ Some dependencies failed to install.")
                    response = input("Continue anyway? (y/n): ")
                    if response.lower() not in ['y', 'yes']:
                        sys.exit(1)
            else:
                print("⚠️  Continuing with missing dependencies...")
                print("💡 You can install dependencies later from the Dependencies tab.")
        else:
            print("✅ All dependencies are installed!")
    
    def setup_window(self):
        self.app.title("KingzVPN Pro - Advanced VPN Client")
        self.app.geometry("1200x800")
        self.app.minsize(1000, 700)
        
        # Center window
        self.app.update_idletasks()
        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        x = (screen_width - 1200) // 2
        y = (screen_height - 800) // 2
        self.app.geometry(f"1200x800+{x}+{y}")
        
        # Set window icon (if available)
        try:
            self.app.iconbitmap(default='icon.ico')
        except:
            pass

    # === ENHANCED DEPENDENCY MANAGEMENT UI ===
    def show_dependency_manager(self):
        """Show enhanced dependency management dialog"""
        dialog = ctk.CTkToplevel(self.app)
        dialog.title("Dependency Manager")
        dialog.geometry("700x500")
        dialog.transient(self.app)
        dialog.grab_set()
        
        # Title
        title = ctk.CTkLabel(dialog, text="📦 Dependency Manager", 
                           font=("Arial", 20, "bold"))
        title.pack(pady=10)
        
        # System info
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(fill="x", padx=20, pady=5)
        
        sys_info = f"Python {platform.python_version()} | {platform.system()} {platform.release()}"
        ctk.CTkLabel(info_frame, text=sys_info, font=("Arial", 11)).pack(pady=5)
        
        # Status summary
        summary_frame = ctk.CTkFrame(dialog)
        summary_frame.pack(fill="x", padx=20, pady=5)
        
        # Count installed vs missing
        total_packages = len(self.dep_manager.required_packages)
        if platform.system() == 'Windows':
            total_packages += len(self.dep_manager.windows_packages)
            
        installed_count = 0
        for pkg in self.dep_manager.required_packages:
            if self.dep_manager.is_package_installed(pkg):
                installed_count += 1
                
        if platform.system() == 'Windows':
            for pkg in self.dep_manager.windows_packages:
                if self.dep_manager.is_package_installed(pkg):
                    installed_count += 1
        
        status_text = f"📊 Status: {installed_count}/{total_packages} packages installed"
        ctk.CTkLabel(summary_frame, text=status_text, font=("Arial", 14, "bold")).pack()
        
        # Dependency list in scrollable frame
        deps_frame = ctk.CTkScrollableFrame(dialog, height=250)
        deps_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Required packages
        ctk.CTkLabel(deps_frame, text="Required Packages:", 
                    font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 5))
        
        for pkg, import_name in self.dep_manager.required_packages.items():
            status = "✅" if self.dep_manager.is_package_installed(pkg) else "❌"
            dep_text = f"   {status} {pkg} -> {import_name}"
            ctk.CTkLabel(deps_frame, text=dep_text, font=("Arial", 11)).pack(anchor="w")
        
        # Windows packages
        if platform.system() == 'Windows':
            ctk.CTkLabel(deps_frame, text="\nWindows Packages:", 
                        font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
            
            for pkg, import_name in self.dep_manager.windows_packages.items():
                status = "✅" if self.dep_manager.is_package_installed(pkg) else "❌"
                dep_text = f"   {status} {pkg} -> {import_name}"
                ctk.CTkLabel(deps_frame, text=dep_text, font=("Arial", 11)).pack(anchor="w")
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        # Install button
        install_btn = ctk.CTkButton(
            btn_frame, 
            text="🔧 Install All Dependencies",
            command=lambda: self._install_deps_from_dialog(dialog),
            fg_color="#28a745",
            hover_color="#218838"
        )
        install_btn.pack(side="left", padx=5)
        
        # Create requirements file button
        req_btn = ctk.CTkButton(
            btn_frame,
            text="📄 Create Requirements File",
            command=lambda: self.dep_manager.create_requirements_file(),
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        req_btn.pack(side="left", padx=5)
        
        # Close button
        close_btn = ctk.CTkButton(
            btn_frame,
            text="❌ Close",
            command=dialog.destroy
        )
        close_btn.pack(side="right", padx=5)
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Refresh",
            command=lambda: self._refresh_dependency_dialog(dialog)
        )
        refresh_btn.pack(side="right", padx=5)

    def _install_deps_from_dialog(self, dialog):
        """Install dependencies from dialog with progress"""
        # Disable install button during installation
        for widget in dialog.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkButton) and "Install" in child.cget("text"):
                        child.configure(state="disabled")
        
        # Show progress label
        progress_label = ctk.CTkLabel(dialog, text="🔄 Installing dependencies...", 
                                    font=("Arial", 12, "bold"))
        progress_label.pack(pady=5)
        
        def install_async():
            try:
                success = self.dep_manager.install_all_dependencies()
                
                def update_ui():
                    progress_label.destroy()
                    
                    if success:
                        # Show success message
                        success_label = ctk.CTkLabel(
                            dialog, 
                            text="✅ Dependencies installed successfully!", 
                            font=("Arial", 12, "bold"),
                            text_color="#28a745"
                        )
                        success_label.pack(pady=5)
                        
                        # Ask to restart
                        response = messagebox.askyesno(
                            "Restart Required", 
                            "Dependencies installed successfully!\n\n"
                            "Restart application for changes to take effect?"
                        )
                        if response:
                            os.execv(sys.executable, [sys.executable] + sys.argv)
                    else:
                        # Show error message
                        error_label = ctk.CTkLabel(
                            dialog, 
                            text="❌ Some dependencies failed to install", 
                            font=("Arial", 12, "bold"),
                            text_color="#dc3545"
                        )
                        error_label.pack(pady=5)
                        
                        # Show solution tips
                        tips_label = ctk.CTkLabel(
                            dialog,
                            text="💡 Check console for details and solutions",
                            font=("Arial", 10)
                        )
                        tips_label.pack(pady=2)
                
                dialog.after(0, update_ui)
                
            except Exception as e:
                def show_error():
                    progress_label.destroy()
                    error_label = ctk.CTkLabel(
                        dialog, 
                        text=f"❌ Installation failed: {str(e)}", 
                        font=("Arial", 12, "bold"),
                        text_color="#dc3545"
                    )
                    error_label.pack(pady=5)
                
                dialog.after(0, show_error)
        
        threading.Thread(target=install_async, daemon=True).start()

    def _refresh_dependency_dialog(self, dialog):
        """Refresh dependency dialog"""
        dialog.destroy()
        self.show_dependency_manager()

    # === SIMPLIFIED CLIPBOARD SYSTEM ===
    def setup_clipboard_support(self):
        """Simplified clipboard support that just works"""
        try:
            # Get the underlying tkinter entry
            tk_entry = self.url_entry._entry
            
            # Bind paste events
            tk_entry.bind('<Control-v>', self._handle_paste_simple)
            tk_entry.bind('<Control-V>', self._handle_paste_simple)
            
            # Right-click context menu
            tk_entry.bind('<Button-3>', self._show_simple_context_menu)
            
            print("✅ Clipboard support initialized")
            
        except Exception as e:
            print(f"❌ Clipboard setup failed: {e}")

    def _handle_paste_simple(self, event):
        """Simple non-blocking paste handler"""
        try:
            # Use tkinter's built-in clipboard (most reliable)
            clipboard_content = self.app.clipboard_get()
            
            if clipboard_content:
                # Insert at cursor position
                event.widget.insert('insert', clipboard_content)
                self.show_notification("Text pasted successfully", "success")
            
            return "break"  # Prevent default handling
            
        except Exception as e:
            print(f"❌ Paste failed: {e}")
            self.show_notification("Paste failed", "error")
            return "break"

    def _show_simple_context_menu(self, event):
        """Simple context menu"""
        try:
            menu = tk.Menu(self.app, tearoff=0)
            menu.add_command(label="Paste", command=lambda: self._handle_paste_simple(event))
            menu.add_separator()
            menu.add_command(label="Copy", command=self._context_copy_simple)
            menu.add_command(label="Cut", command=self._context_cut_simple)
            menu.add_command(label="Select All", command=self._context_select_all_simple)
            
            menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            print(f"❌ Context menu failed: {e}")

    def _context_copy_simple(self):
        """Simple copy operation"""
        try:
            selected_text = self.url_entry.get()
            if selected_text:
                self.app.clipboard_clear()
                self.app.clipboard_append(selected_text)
                self.show_notification("Text copied", "success")
        except Exception as e:
            print(f"❌ Copy failed: {e}")

    def _context_cut_simple(self):
        """Simple cut operation"""
        try:
            selected_text = self.url_entry.get()
            if selected_text:
                self.app.clipboard_clear()
                self.app.clipboard_append(selected_text)
                self.url_entry.delete(0, 'end')
                self.show_notification("Text cut", "success")
        except Exception as e:
            print(f"❌ Cut failed: {e}")

    def _context_select_all_simple(self):
        """Simple select all"""
        try:
            self.url_entry._entry.select_range(0, 'end')
            self.url_entry._entry.icursor('end')
        except Exception as e:
            print(f"❌ Select all failed: {e}")

    # === CORE APPLICATION FUNCTIONALITY ===
    def setup_database(self):
        """Initialize SQLite database"""
        try:
            self.db_conn = sqlite3.connect(os.path.join(DB_DIR, 'vpn_client.db'))
            self.db_cursor = self.db_conn.cursor()
            
            # Create basic tables
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS connection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    server_name TEXT,
                    config_type TEXT,
                    duration INTEGER,
                    success BOOLEAN
                )
            ''')
            
            self.db_conn.commit()
            self.logger.info("Database initialized")
            
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")

    def load_user_preferences(self):
        """Load user preferences"""
        try:
            self.db_cursor.execute("SELECT key, value FROM user_preferences")
            preferences = self.db_cursor.fetchall()
            
            self.user_prefs = {key: value for key, value in preferences}
            self.logger.info("User preferences loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load preferences: {e}")
            self.user_prefs = {}

    def save_user_preference(self, key, value):
        """Save user preference"""
        try:
            self.db_cursor.execute(
                "INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.db_conn.commit()
            self.user_prefs[key] = value
        except Exception as e:
            self.logger.error(f"Failed to save preference: {e}")

    def load_data(self):
        """Load initial data"""
        self.preset_servers = [
            {"name": "USA - New York Premium", "address": "nyc.example.com", "ping": 28, "load": 45, "type": "premium"},
            {"name": "Germany - Frankfurt Secure", "address": "fra.example.com", "ping": 35, "load": 32, "type": "secure"},
            {"name": "UK - London Streaming", "address": "lon.example.com", "ping": 42, "load": 28, "type": "streaming"},
        ]

    # === UI CREATION ===
    def create_ui(self):
        """Create the main UI"""
        # Main container
        self.main_container = ctk.CTkFrame(self.app, fg_color=self.colors["dark_bg"])
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Create sidebar and main content
        self.create_sidebar()
        self.create_main_content()
        
        # Initialize tabs
        self.create_quick_connect_tab()
        self.create_tools_tab()
        self.create_dependencies_tab()
        
        self.show_quick_connect()

    def create_sidebar(self):
        """Create sidebar navigation"""
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=250,
            corner_radius=0,
            fg_color=self.colors["card_bg"]
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Logo section
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(20, 10), padx=15)
        
        self.logo_label = ctk.CTkLabel(
            logo_frame,
            text="KingzVPN Pro",
            font=("Arial", 18, "bold"),
            text_color=self.colors["primary"]
        )
        self.logo_label.pack()
        
        # Version info
        ctk.CTkLabel(
            logo_frame,
            text="v2.0 | Stable",
            font=("Arial", 10),
            text_color=self.colors["text_secondary"]
        ).pack(pady=(5, 0))
        
        self.create_navigation()
        self.create_sidebar_status()

    def create_navigation(self):
        """Create navigation buttons"""
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15, pady=10)
        
        nav_buttons = [
            ("🚀 Quick Connect", self.show_quick_connect),
            ("🛠️ Tools", self.show_tools),
            ("📦 Dependencies", self.show_dependency_manager),
        ]
        
        for text, command in nav_buttons:
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                font=("Arial", 12),
                height=35,
                fg_color="transparent",
                text_color=self.colors["text_secondary"],
                hover_color=("gray60", "gray30"),
                anchor="w",
                command=command
            )
            btn.pack(fill="x", pady=1)
            self.nav_buttons[text] = btn

    def create_sidebar_status(self):
        """Create status section in sidebar"""
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=15, pady=15)
        
        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="● OFFLINE",
            font=("Arial", 12, "bold"),
            text_color=self.colors["danger"]
        )
        self.status_indicator.pack(anchor="w")
        
        self.ip_label = ctk.CTkLabel(
            status_frame,
            text="IP: Loading...",
            font=("Arial", 10),
            text_color=self.colors["text_secondary"]
        )
        self.ip_label.pack(anchor="w")
        
        threading.Thread(target=self.load_ip_info, daemon=True).start()

    def create_main_content(self):
        """Create main content area"""
        self.main_content = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    def create_quick_connect_tab(self):
        """Create quick connect tab"""
        self.quick_connect_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        
        title = ctk.CTkLabel(
            self.quick_connect_frame,
            text="Quick Connect",
            font=("Arial", 24, "bold")
        )
        title.pack(anchor="w", pady=(0, 20))
        
        # Import section
        import_card = ctk.CTkFrame(
            self.quick_connect_frame,
            corner_radius=10,
            fg_color=self.colors["card_bg"]
        )
        import_card.pack(fill="x", pady=10)
        
        content_frame = ctk.CTkFrame(import_card, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            content_frame,
            text="Import VPN Configuration",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        url_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        url_frame.pack(fill="x")
        
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Enter config URL or paste with Ctrl+V...",
            height=40,
            font=("Arial", 12)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Setup clipboard support
        self.setup_clipboard_support()
        
        import_btn = ctk.CTkButton(
            url_frame,
            text="Import",
            height=40,
            width=100,
            font=("Arial", 12),
            fg_color=self.colors["secondary"],
            command=self.import_config
        )
        import_btn.pack(side="right")

    def create_tools_tab(self):
        """Create tools tab"""
        self.tools_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        
        title = ctk.CTkLabel(
            self.tools_frame,
            text="Tools",
            font=("Arial", 24, "bold")
        )
        title.pack(anchor="w", pady=(0, 20))
        
        # Tools grid
        tools_grid = ctk.CTkFrame(self.tools_frame, fg_color="transparent")
        tools_grid.pack(fill="both", expand=True)
        
        # Basic tools card
        tools_card = ctk.CTkFrame(
            tools_grid,
            corner_radius=10,
            fg_color=self.colors["card_bg"]
        )
        tools_card.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(
            tools_card,
            text="Basic Tools",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        # Add basic tool buttons
        self.add_tool_button(tools_card, "Generate Password", 
                           lambda: self.show_notification(f"Password: {self.generate_strong_password()}", "info"))
        
        self.add_tool_button(tools_card, "Test Connection", 
                           lambda: self.test_connection())

    def create_dependencies_tab(self):
        """Create dependencies tab placeholder"""
        self.deps_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")

    def add_tool_button(self, parent, text, command):
        """Add tool button to card"""
        btn = ctk.CTkButton(
            parent,
            text=text,
            font=("Arial", 12),
            height=35,
            fg_color=self.colors["secondary"],
            command=command
        )
        btn.pack(fill="x", padx=10, pady=5)

    # === UTILITY FUNCTIONS ===
    def generate_strong_password(self, length=16):
        """Generate strong random password"""
        try:
            characters = string.ascii_letters + string.digits + "!@#$%&*"
            password = ''.join(secrets.choice(characters) for _ in range(length))
            return password
        except Exception as e:
            return "Error generating password"

    def test_connection(self):
        """Test internet connection"""
        try:
            response = requests.get('https://www.google.com', timeout=5)
            if response.status_code == 200:
                self.show_notification("Internet connection: OK", "success")
            else:
                self.show_notification("Internet connection: Failed", "error")
        except Exception as e:
            self.show_notification("Internet connection: Failed", "error")

    def load_ip_info(self):
        """Load public IP information"""
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            ip = response.text
            self.app.after(0, lambda: self.ip_label.configure(text=f"IP: {ip}"))
        except:
            self.app.after(0, lambda: self.ip_label.configure(text="IP: Unavailable"))

    def import_config(self):
        """Import configuration from URL"""
        try:
            url = self.url_entry.get().strip()
            if not url:
                self.show_notification("Please enter a URL", "warning")
                return
                
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                self.show_notification("Please enter a valid URL", "error")
                return
                
            self.show_notification(f"Importing from: {url}", "info")
            # Actual import logic would go here
            
        except Exception as e:
            self.show_notification(f"Import failed: {str(e)}", "error")

    def show_notification(self, message, type_="info"):
        """Show notification message"""
        try:
            colors = {
                "success": self.colors["success"],
                "error": self.colors["danger"], 
                "warning": self.colors["warning"],
                "info": self.colors["secondary"]
            }
            bg_color = colors.get(type_, self.colors["secondary"])
            
            def create_notification():
                try:
                    notification = ctk.CTkFrame(
                        self.app,
                        corner_radius=8,
                        fg_color=bg_color
                    )
                    notification.place(relx=0.5, rely=0.1, anchor="center")
                    
                    label = ctk.CTkLabel(
                        notification,
                        text=message,
                        text_color="white",
                        font=("Arial", 11)
                    )
                    label.pack(padx=15, pady=8)
                    
                    self.app.after(3000, notification.destroy)
                    
                except Exception as e:
                    pass
                    
            self.app.after(0, create_notification)
            
        except Exception as e:
            pass

    # === TAB MANAGEMENT ===
    def show_quick_connect(self):
        """Show quick connect tab"""
        self.hide_all_tabs()
        if self.quick_connect_frame:
            self.quick_connect_frame.pack(fill="both", expand=True)
        self.highlight_nav_button("🚀 Quick Connect")

    def show_tools(self):
        """Show tools tab"""
        self.hide_all_tabs()
        if self.tools_frame:
            self.tools_frame.pack(fill="both", expand=True)
        self.highlight_nav_button("🛠️ Tools")

    def hide_all_tabs(self):
        """Hide all tabs"""
        frames = [self.quick_connect_frame, self.tools_frame, self.deps_frame]
        for frame in frames:
            if frame:
                try:
                    frame.pack_forget()
                except:
                    pass

    def highlight_nav_button(self, button_text):
        """Highlight active navigation button"""
        for text, btn in self.nav_buttons.items():
            if text == button_text:
                btn.configure(fg_color=("gray60", "gray30"))
            else:
                btn.configure(fg_color="transparent")

    # === LOGGING AND CLEANUP ===
    def setup_logging(self):
        """Setup logging system"""
        try:
            self.logger = logging.getLogger('KingzVPNPro')
            self.logger.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            
            # Console handler only for simplicity
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            
            self.logger.handlers.clear()
            self.logger.addHandler(console_handler)
            
            self.logger.info("KingzVPN Pro started")
            
        except Exception as e:
            print(f"Logging setup failed: {e}")
            self.logger = logging.getLogger('KingzVPNPro')

    def run(self):
        """Run the application"""
        try:
            self.logger.info("Starting KingzVPN Pro")
            self.app.mainloop()
            
        except Exception as e:
            self.logger.error(f"Application failed: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        try:
            # Stop all threads
            for event in self.events.values():
                event.set()
                
            # Close database
            if hasattr(self, 'db_conn'):
                self.db_conn.close()
                
            self.logger.info("Application cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

# ===== MAIN EXECUTION =====
def main():
    print("🎯 KingzVPN Pro - Advanced VPN Client")
    print("=" * 50)
    
    # Check command line arguments
    auto_install = '--no-install' not in sys.argv
    
    if auto_install:
        print("🔍 Auto-installation enabled")
    else:
        print("🔍 Auto-installation disabled")
    
    try:
        # Create and run application
        vpn_app = AdvancedVPNClient(auto_install_deps=auto_install)
        vpn_app.run()
        
    except KeyboardInterrupt:
        print("\n👋 Application interrupted by user")
    except Exception as e:
        print(f"💥 Critical error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()