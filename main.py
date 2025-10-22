import customtkinter as ctk
from pathlib import Path
import os

app = ctk.CTk()

# Пробуем установить иконку
try:
	# Получаем абсолютный путь к файлу иконки
	current_dir = os.path.dirname(os.path.abspath(__file__))
	icon_path = os.path.join(current_dir, "app.ico")
    
    
	if os.path.exists(icon_path):
		app.iconbitmap(icon_path)
	else:
		print("Ошибка: файл иконки не найден")
except Exception as e:
	print(f"Ошибка при установке иконки: {str(e)}")

app.title("KingzVPN")
app.geometry("800x800")
app.mainloop()