import cv2
import numpy as np
import mss
import mss.tools
import win32gui
import win32ui
from ctypes import windll
import pygetwindow as gw
from PyQt5.QtGui import (QPainter, QPen, QColor)
from PyQt5.QtWidgets import (QMainWindow, QApplication)
from PyQt5.QtCore import (Qt, pyqtSignal, QObject)
import threading
from nudenet import NudeDetector
import time
from skimage.metrics import structural_similarity as ssim
from utils import delete_rename_file

SCREEN_IMAGE_PATH = "./inputs/input.png"
CURRENT_SCREEN_IMAGE_PATH = "./inputs/current-input.png"
CURRENT_SCREEN_BMP_PATH = "./inputs/current-input.bmp"
CENSOR_SCREEN_IMAGE_PATH = "./inputs/input-censored.png"
IMAGE_SIMILARITY = 90      # for now use similarity to check whether images are the same (before and after censored)

class Communicate(QObject):
    position = pyqtSignal(int, int, int, int)
    isNotSexual = pyqtSignal(bool)

class TransparentWindow(QMainWindow):
    def __init__(
            self,
            x: int,
            y: int,
            width: int,
            height: int,
            pen_color: str,
            pen_size: int):
        super().__init__()
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self.pen_color = pen_color
        self.pen_size = pen_size
        # Set window flag to stay on top
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.initUI()

    def initUI(self):
        """Initialize the user interface of the window."""
        self.setGeometry(
            self._x,
            self._y,
            self._width + self.pen_size,
            self._height + self.pen_size)
        self.setStyleSheet('background: transparent')
        self.setWindowFlag(Qt.FramelessWindowHint)

    def paintEvent(self, event):
        """Paint the user interface."""
        painter = QPainter()
        painter.begin(self)
        painter.setPen(QPen(QColor(self.pen_color), self.pen_size))
        painter.drawRect(
            self.pen_size - 1,
            self.pen_size - 1,
            self.width() - 2 * self.pen_size,
            self.height() - 2 * self.pen_size)
        painter.end()

nude_detector = NudeDetector()
app = QApplication([])
comm = Communicate()
censor_blocks = []

def capture_save_screen():
    # with mss.mss() as sct:
    #     monitor = sct.monitors[1]  # Capture the primary monitor
    #     screenshot = sct.grab(monitor)

    #     # Convert the screenshot to a numpy array
    #     img = np.array(screenshot)
    #     # Convert the image from BGRA to BGR (removing the alpha channel)
    #     img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    #     cv2.imwrite(CURRENT_SCREEN_IMAGE_PATH, img_bgr)

    window_name = gw.getActiveWindowTitle()
    # print(window_name)

    try:
        # Adapted from https://stackoverflow.com/questions/19695214/screenshot-of-inactive-window-printwindow-win32gui
        hwnd = win32gui.FindWindow(None, window_name)

        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        w = right - left
        h = bottom - top

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bitmap)

        # If Special K is running, this number is 3. If not, 1
        result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)

        img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4))
        img = np.ascontiguousarray(img)[..., :-1]  # make image C_CONTIGUOUS and drop alpha channel

        if not result:  # result should be 1
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            raise RuntimeError(f"Unable to acquire screenshot! Result: {result}")

        cv2.imwrite(CURRENT_SCREEN_IMAGE_PATH, img)
    except:
        cv2.imwrite(CURRENT_SCREEN_IMAGE_PATH, cv2.imread(SCREEN_IMAGE_PATH))

def capture_and_censor_screen(detection_areas, censor_mode=''):
    # Pixelate function
    def pixelate_area(image, top_left, bottom_right, blocks=10):
        # Extract the region of interest (ROI)
        x1, y1 = top_left
        x2, y2 = bottom_right
        roi = image[y1:y2, x1:x2]

        # Pixelate the ROI
        height, width = roi.shape[:2]
        temp = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
        roi_pixelated = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Replace the ROI in the original image with the pixelated ROI
        image[y1:y2, x1:x2] = roi_pixelated
        return image

    # Blur function
    def blur_area(image, top_left, bottom_right, ksize=(25, 25)):
        # Extract the region of interest (ROI)
        x1, y1 = top_left
        x2, y2 = bottom_right
        roi = image[y1:y2, x1:x2]

        # Apply Gaussian blur to the ROI
        roi_blurred = cv2.GaussianBlur(roi, ksize, 0)

        # Replace the ROI in the original image with the blurred ROI
        image[y1:y2, x1:x2] = roi_blurred
        return image

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Use the first monitor
        while True:
            screenshot = np.array(sct.grab(monitor))

            # Remove the alpha channel (mss returns BGRA)
            frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

            for area in detection_areas:
                box = area.get('box')
                x = box[0]
                y = box[1]
                width = box[2]
                height = box[3]
                # Censor the specified area
                if censor_mode == 'blur':
                    frame = blur_area(frame, (x, y), (x + width, y+ height))
                elif censor_mode == 'pixelate':
                    frame = pixelate_area(frame, (x, y), (x + width, y+ height))
                send_draw_censor_block_signal(x, y, width, height)

            # cv2.imshow('Censored Screen', frame)
            cv2.imwrite(CENSOR_SCREEN_IMAGE_PATH, frame)
            break

    cv2.destroyAllWindows()

def send_draw_censor_block_signal(x: int, y: int, width: int, height: int):
    comm.position.emit(x, y, width, height)
    comm.isNotSexual.emit(False)

def send_clear_censor_block_signal():
    comm.isNotSexual.emit(True)

def clear_censor_blocks(isNotSexual):
    if isNotSexual:
        global censor_blocks
        for block in censor_blocks:
            # block.close()
            block.hide()
        censor_blocks = []

def draw_censor_block(
    x: int,
    y: int,
    width: int,
    height: int,
    pen_color: str = '#00ff00',
    pen_size: int = 2):
        """ 
        Censors an area as a rectangle on the main screen.
            -> `x`: x position of the rectangle

            -> `y`: y position of the rectangle

            -> `width`: width of the rectangle

            -> `height`: height of the rectangle

            -> `pen_color` (Optional): color of the rectangle as a hex value; defaults to `#000000`

            -> `pen_size` (Optional): border size of the rectangle; defaults to 2
        """
        global censor_blocks
        window = TransparentWindow(x, y, width, height, pen_color, pen_size)
        window.show()
        censor_blocks.append(window)

def check_image_similarity(image1_path, image2_path):
    # Read the images in grayscale mode
    image1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
    image2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
    (H, W) = image1.shape
    image2 = cv2.resize(image2, (W, H))

    if image1 is None or image2 is None:
        raise ValueError("One of the images could not be read. Please check the file paths.")

    if image1.shape != image2.shape:
        raise ValueError("The images have different dimensions and cannot be compared.")

    # Compute SSIM between two images
    score, _ = ssim(image1, image2, full=True)
    similarity_percentage = score * 100
    return similarity_percentage > IMAGE_SIMILARITY

def censoring_task():
    time.sleep(1)
    while True:
        capture_save_screen()
        if (not check_image_similarity(CURRENT_SCREEN_IMAGE_PATH, SCREEN_IMAGE_PATH)):
            send_clear_censor_block_signal()
            # If images (current and previous) are not similar
            delete_rename_file(CURRENT_SCREEN_IMAGE_PATH, SCREEN_IMAGE_PATH)
            detections = nude_detector.detect(SCREEN_IMAGE_PATH)
            # print(detections)
            if len(detections) > 0: capture_and_censor_screen(detections)
            else: send_clear_censor_block_signal()

def start_exec():    
    censorer_thread = threading.Thread(target=censoring_task)
    censorer_thread.start()
    comm.position.connect(draw_censor_block)
    comm.isNotSexual.connect(clear_censor_blocks)
    app.exec_()