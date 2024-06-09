import pprint
import cv2
import numpy as np
import mss
import mss.tools

SCREEN_IMAGE_PATH = "./inputs/input.png"
CENSOR_SCREEN_IMAGE_PATH = "./inputs/input-censored.png"

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

def capture_and_censor_screen(detection_areas, censor_mode='pixelate'):
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

            # cv2.imshow('Censored Screen', frame)
            cv2.imwrite(CENSOR_SCREEN_IMAGE_PATH, frame)
            break

            # Break the loop when 'q' key is pressed
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

    cv2.destroyAllWindows()