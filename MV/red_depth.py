import pyrealsense2 as rs
import numpy as np
import cv2
import math


def classify_shape(contour):
    """
    Classify a contour as 'circle', 'cylinder', or None.
    Uses circularity and aspect ratio.
    """

    area = cv2.contourArea(contour)
    if area <= 0:
        return None

    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0:
        return None

    # Circularity: 1.0 = perfect circle
    circularity = 4 * math.pi * (area / (perimeter * perimeter))

    x, y, w, h = cv2.boundingRect(contour)
    if w == 0 or h == 0:
        return None

    aspect_ratio = max(w, h) / min(w, h)  # >= 1

    # Heuristic rules (tune as needed):
    # - Circle: nearly equal width/height and high circularity
    if aspect_ratio < 1.3 and circularity > 0.7:
        return "circle"

    # - Cylinder-like: more elongated shape (seen as rectangle/oval in image)
    #   Here we just use aspect ratio; you can also add extra rules if needed.
    if aspect_ratio >= 1.3:
        return "cylinder"

    return None


def display_red_clusters_with_shape_and_depth():
    pipeline = rs.pipeline()
    config = rs.config()

    # Streams
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # Align depth to color so pixel coordinates match
    align_to = rs.stream.color
    align = rs.align(align_to)

    try:
        pipeline.start(config)

        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)

            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # Depth visualization
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03),
                cv2.COLORMAP_JET
            )

            # HSV conversion
            hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)

            # Red mask
            lower_red1 = np.array([0, 150, 120])
            upper_red1 = np.array([8, 255, 255])
            lower_red2 = np.array([172, 150, 120])
            upper_red2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask_red = cv2.bitwise_or(mask1, mask2)

            # Clean noise
            kernel = np.ones((3, 3), np.uint8)
            mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel)
            mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_DILATE, kernel)

            # Red-only image
            red_only = cv2.bitwise_and(color_image, color_image, mask=mask_red)

            # Edges on red region
            red_gray = cv2.cvtColor(red_only, cv2.COLOR_BGR2GRAY)
            red_edges = cv2.Canny(red_gray, 50, 150)
            edges_bgr = cv2.cvtColor(red_edges, cv2.COLOR_GRAY2BGR)

            # Contours on red mask
            contours, _ = cv2.findContours(
                mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            MIN_AREA = 500  # ignore tiny blobs

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < MIN_AREA:
                    continue

                shape = classify_shape(cnt)
                if shape is None:
                    # Ignore red blobs that are not circle/cylinder-like
                    continue

                x, y, w, h = cv2.boundingRect(cnt)
                cx = x + w // 2
                cy = y + h // 2

                # Depth at center
                distance = depth_frame.get_distance(cx, cy)  # meters

                # Draw bounding box on edges image
                cv2.rectangle(edges_bgr, (x, y), (x + w, y + h),
                              (0, 0, 255), 2)

                # Label with shape + depth
                label = f"{shape.capitalize()} {distance:.2f} m"
                text_pos = (x, y - 10 if y - 10 > 0 else y + 20)
                cv2.putText(edges_bgr, label, text_pos,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 255, 0), 1, cv2.LINE_AA)

            # Show windows
            cv2.imshow("Color Stream", color_image)
            cv2.imshow("Depth Stream", depth_colormap)
            cv2.imshow("Red Only", red_only)
            cv2.imshow("Red Edges + Shape + Depth", edges_bgr)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    display_red_clusters_with_shape_and_depth()