import os
import time

import pyautogui

file_path = os.path.join(os.path.dirname(__file__), "image", "fish.png")


def AutoFish():
    if not os.path.exists(file_path):
        print("File not found.")
        return

    try:
        # 画像の検出
        fish_location = pyautogui.locateOnScreen(file_path, confidence=0.8)
        if fish_location:
            center_x, center_y = pyautogui.center(fish_location)
            print("fishing")
            pyautogui.mouseDown(center_x, center_y, button="right")
            time.sleep(1)
            pyautogui.mouseUp(button="right")
            time.sleep(0.5)
            pyautogui.mouseDown(center_x, center_y, button="right")
            time.sleep(0.5)
            pyautogui.mouseUp(button="right")

    except Exception as e:
        pass


if __name__ == "__main__":
    while True:
        AutoFish()
