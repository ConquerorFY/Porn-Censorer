from nudenet import NudeDetector
from utils import capture_and_censor_screen, capture_save_screen, SCREEN_IMAGE_PATH

nude_detector = NudeDetector()

while True:
    capture_save_screen()
    detections = nude_detector.detect(SCREEN_IMAGE_PATH)
    nude_detector.censor(SCREEN_IMAGE_PATH)
    print(detections)
    if len(detections) > 0: break

# capture_and_censor_screen(detections)