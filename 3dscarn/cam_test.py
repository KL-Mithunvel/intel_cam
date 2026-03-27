import sys

print("Python:", sys.version)

try:
    import pyrealsense2 as rs
    print("pyrealsense2 OK")
except Exception as e:
    print("pyrealsense2 ERROR:", e)

try:
    import open3d as o3d
    print("open3d OK")
except Exception as e:
    print("open3d ERROR:", e)

try:
    import cv2
    print("opencv OK, version:", cv2.__version__)
except Exception as e:
    print("opencv ERROR:", e)