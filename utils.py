import pprint
import cv2
import numpy as np
import mss
import mss.tools

SCREEN_IMAGE_PATH = "./inputs/input.png"

pp = pprint.PrettyPrinter(indent=1, width=80, depth=None)

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
        cv2.imwrite(SCREEN_IMAGE_PATH, img_bgr)

def capture_and_censor_screen(area, censor_mode='pixelate'):
    print(area)
    # Pixelate function
    def pixelate_area(image, blocks=10):
        height, width = image.shape[:2]
        temp = cv2.resize(image, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

    # Blur function
    def blur_area(image, ksize=(25, 25)):
        return cv2.GaussianBlur(image, ksize, 0)

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Use the first monitor
        while True:
            screenshot = np.array(sct.grab(monitor))

            # Remove the alpha channel (mss returns BGRA)
            frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

            # Censor the specified area
            if censor_mode == 'blur':
                censored_frame = blur_area(frame)
            elif censor_mode == 'pixelate':
                censored_frame = pixelate_area(frame)
            else:
                censored_frame = frame

            cv2.imshow('Censored Screen', censored_frame)

            # Break the loop when 'q' key is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()