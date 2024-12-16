import tkinter as tk
from tkinter import messagebox

import pyautogui


def take_screenshot():
    # スクショを撮る領域を指定（例：左上座標 (100, 100)、幅500、高さ400）
    x, y, width, height = 100, 100, 500, 400
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    # スクショを保存
    save_path = "screenshot.png"
    screenshot.save(save_path)
    messagebox.showinfo("完了", f"スクリーンショットを保存しました: {save_path}")


# Tkinterでウインドウを作成
root = tk.Tk()
root.title("スクリーンショットツール")

# ボタンを作成
button = tk.Button(root, text="スクショを撮る", command=take_screenshot)
button.pack(pady=20)

# ウインドウを表示
root.geometry("500x200")
root.mainloop()
