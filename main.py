from nudenet import NudeDetector
from utils import print

nude_detector = NudeDetector()
input = 'inputs/input-1.png'

detections = nude_detector.detect(input)
print(detections)
nude_detector.censor(input)