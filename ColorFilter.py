import sys
import numpy as np
import pyautogui
from PyQt5.QtWidgets import (QApplication, QWidget,)
from PyQt5.QtGui import QPainter, QColor, QImage
from PyQt5.QtCore import Qt, QTimer
import keyboard  

import ctypes
import platform

def set_window_click_through(winId):
    """
    Makes the window click-through (ignores mouse events) on Windows.
    """
    if platform.system() == "Windows":

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020

        hwnd = int(winId)
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)




class EyedropperOverlay(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setup_window()
        
    def setup_window(self):
        screen = QApplication.primaryScreen().geometry()
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.3)
        self.setGeometry(screen.x(), screen.y(), screen.width(), screen.height())
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.globalX(), event.globalY()
            screenshot = pyautogui.screenshot()
            pixel = screenshot.getpixel((x, y))
            rgb = np.array(pixel[:3])  
            self.callback(rgb)
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 50))
        

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignCenter, 
                        "Click any color to select it\nESC to cancel")

class ColorOverlay(QWidget):
    def __init__(self, mask):
        super().__init__()
        self.mask = mask
        self.visible = True
        self.current_color = None
        self.tolerance = 3
        self.setup_window()
        self.draw_mask()

    def setup_window(self):

        screen = QApplication.primaryScreen().geometry()
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1.0)
        self.setGeometry(screen.x(), screen.y(), screen.width(), screen.height())
        
        self.image = QImage(screen.width(), screen.height(), QImage.Format_ARGB32)
        self.image.fill(Qt.transparent)


        set_window_click_through(self.winId())

    def draw_mask(self):
        from scipy.ndimage import binary_dilation

        height, width = self.mask.shape
        self.image.fill(Qt.transparent)

        dilated = binary_dilation(self.mask, iterations=6)
        thick_red_border = np.logical_and(dilated, ~self.mask)

        red_color = QColor(255, 0, 0, 200).rgba()

        ys, xs = np.where(thick_red_border)
        for y, x in zip(ys, xs):
            self.image.setPixel(x, y, red_color)

        self.update()


    def update_with_new_rgb(self, rgb, tolerance=None):
        if tolerance is None:
            tolerance = self.tolerance
        
        self.current_color = rgb
        screenshot = pyautogui.screenshot()
        screen_np = np.array(screenshot)
        if screen_np.shape[2] == 4:
            screen_np = screen_np[:, :, :3]
        
        diff = np.abs(screen_np.astype(int) - rgb.astype(int))
        mask = np.all(diff <= tolerance, axis=-1)
        self.mask = mask
        self.draw_mask()

    def toggle_visibility(self):
        if self.visible:
            self.hide()
            self.visible = False
        else:
            self.show()
            self.visible = True

            set_window_click_through(self.winId())

    def open_eyedropper(self):
        def on_color_selected(rgb):
            self.update_with_new_rgb(rgb)
            print(f"[✔] New color selected: RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")
        
        self.eyedropper = EyedropperOverlay(on_color_selected)
        self.eyedropper.show()

    def paintEvent(self, event):
        if self.visible:
            painter = QPainter(self)
            painter.drawImage(0, 0, self.image)

def main():
    app = QApplication(sys.argv)


    print("\n=== CONTROLS ===")
    print("- Press 'X' to show/hide overlay")
    print("- Press 'E' to use eyedropper (select new color)")
    print("- Press 'ESC' to exit")
    print("==================")

    screen = QApplication.primaryScreen().geometry()
    mask = np.zeros((screen.height(), screen.width()), dtype=bool)
    overlay = ColorOverlay(mask)
    overlay.show()

    def on_x_press(event):
        overlay.toggle_visibility()
        print("[ℹ] Overlay", "shown" if overlay.visible else "hidden")

    def on_esc_press(event):
        app.quit()

    def on_e_press(event):
        print("[ℹ] Opening eyedropper...")
        QTimer.singleShot(0, overlay.open_eyedropper)

    keyboard.on_press_key('x', on_x_press)
    keyboard.on_press_key('esc', on_esc_press)
    keyboard.on_press_key('e', on_e_press)

    app.exec_()

if __name__ == "__main__":
    main()