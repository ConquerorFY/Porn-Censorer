import pprint
import sys
import cv2
import numpy as np
import mss
import mss.tools
from PyQt5.QtGui import (QPainter, QPen, QColor)
from PyQt5.QtWidgets import (QMainWindow, QApplication)
from PyQt5.QtCore import Qt
import threading
from nudenet import NudeDetector
import time
import os
from skimage.metrics import structural_similarity as ssim

SCREEN_IMAGE_PATH = "./inputs/input.png"
CURRENT_SCREEN_IMAGE_PATH = "./inputs/current-input.png"
CENSOR_SCREEN_IMAGE_PATH = "./inputs/input-censored.png"
IMAGE_SIMILARITY = 80       # for now use similarity to check whether images are the same (before and after censored)

nude_detector = NudeDetector()
app = QApplication([])
pp = pprint.PrettyPrinter(indent=1, width=80, depth=None)
censor_blocks = []

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
        self.highlight_x = x
        self.highlight_y = y
        self.highlight_width = width
        self.highlight_height = height
        self.pen_color = pen_color
        self.pen_size = pen_size
        # Set window flag to stay on top
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.initUI()

    def initUI(self):
        """Initialize the user interface of the window."""
        self.setGeometry(
            self.highlight_x,
            self.highlight_y,
            self.highlight_width + self.pen_size,
            self.highlight_height + self.pen_size)
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
            self. height() - 2 * self.pen_size)
        painter.end()

def print(args: str):
    pp.pprint(args)

def capture_save_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Capture the primary monitor
        screenshot = sct.grab(monitor)

        # Convert the screenshot to a numpy array
        img = np.array(screenshot)
        # Convert the image from BGRA to BGR (removing the alpha channel)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(CURRENT_SCREEN_IMAGE_PATH, img_bgr)

def capture_and_censor_screen(detection_areas, censor_mode='blur'):
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
                draw_censor_block(x, y, width, height)

            # cv2.imshow('Censored Screen', frame)
            cv2.imwrite(CENSOR_SCREEN_IMAGE_PATH, frame)
            break

    cv2.destroyAllWindows()

def clear_censor_blocks():
    global censor_blocks
    for block in censor_blocks:
        block.close()
        # block.hide()
    censor_blocks = []

def draw_censor_block(
        x: int,
        y: int,
        width: int,
        height: int,
        pen_color: str = '#000000',
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

    if image1 is None or image2 is None:
        raise ValueError("One of the images could not be read. Please check the file paths.")

    if image1.shape != image2.shape:
        raise ValueError("The images have different dimensions and cannot be compared.")

    # Compute SSIM between two images
    score, _ = ssim(image1, image2, full=True)
    similarity_percentage = score * 100

    return similarity_percentage > IMAGE_SIMILARITY

def delete_rename_file(old_name, new_name):
    try:
        os.remove(new_name)
        os.rename(old_name, new_name)
        # print(f"File renamed from {old_name} to {new_name}")
    except FileNotFoundError:
        print(f"The file {old_name} does not exist.")
    except PermissionError:
        print(f"Permission denied to rename the file {old_name}.")
    except Exception as e:
        print(f"An error occurred: {e}")

def censoring_task():
    time.sleep(1)
    while True:
        capture_save_screen()
        if (not check_image_similarity(CURRENT_SCREEN_IMAGE_PATH, SCREEN_IMAGE_PATH)):
            # if images (current and previous) are not similar by 60%
            delete_rename_file(CURRENT_SCREEN_IMAGE_PATH, SCREEN_IMAGE_PATH)
            detections = nude_detector.detect(SCREEN_IMAGE_PATH)
            # print(detections)
            if len(detections) > 0: capture_and_censor_screen(detections)
            else: clear_censor_blocks()

def start_exec():
    censorer_thread = threading.Thread(target=censoring_task)
    censorer_thread.start()
    app.exec_()