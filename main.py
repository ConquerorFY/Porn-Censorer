from nudenet import NudeDetector
from utils import capture_and_censor_screen, capture_save_screen, SCREEN_IMAGE_PATH

nude_detector = NudeDetector()

# ** Sample Detection Output **
# [
#     {
#         'class': 'ARMPITS_EXPOSED', 
#         'score': 0.5383620858192444, 
#         'box': [1576, 568, 58, 70]    # x, y, w, h
#     }, 
#     {
#         'class': 'FACE_FEMALE', 
#         'score': 0.4470580816268921, 
#         'box': [1394, 382, 134, 118]
#     }, 
#     {
#         'class': 'ARMPITS_EXPOSED', 
#         'score': 0.3124203681945801, 
#         'box': [1381, 572, 51, 62]
#     }, 
#     {
#         'class': 'FACE_FEMALE', 
#         'score': 0.26181691884994507, 
#         'box': [982, 680, 62, 58]
#     }
# ]

while True:
    capture_save_screen()
    detections = nude_detector.detect(SCREEN_IMAGE_PATH)
    if len(detections) > 0:
        capture_and_censor_screen(detections)
