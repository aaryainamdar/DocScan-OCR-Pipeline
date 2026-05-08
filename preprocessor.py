"""
pipeline/preprocessor.py
------------------------
Handles all image preprocessing before OCR:
  - Auto-rotation / deskewing
  - Edge detection & perspective transformation (document scan correction)
  - Denoising
  - Contrast & brightness enhancement (CLAHE)
  - Adaptive thresholding / binarization
"""

import os
import cv2
import numpy as np


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def preprocess_image(input_path: str, output_dir: str, doc_id: str, enhance: bool = True):
    """
    Full preprocessing pipeline.

    Returns
    -------
    preprocessed_path : str
        Path to the processed image ready for OCR.
    stats : dict
        Metadata about what was applied.
    """
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image: {input_path}")

    stats = {
        'original_size': list(img.shape[:2]),
        'steps_applied': []
    }

    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    stats['steps_applied'].append('grayscale')

    # 2. Deskew
    gray, angle = _deskew(gray)
    stats['deskew_angle_deg'] = round(angle, 2)
    stats['steps_applied'].append('deskew')

    # 3. Perspective / document boundary detection
    warped = _perspective_transform(img, gray)
    if warped is not None:
        gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        stats['steps_applied'].append('perspective_transform')

    if enhance:
        # 4. Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        stats['steps_applied'].append('denoise')

        # 5. CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        stats['steps_applied'].append('clahe_contrast')

    # 6. Adaptive binarization (Otsu's thresholding)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    stats['steps_applied'].append('otsu_binarization')

    # 7. Morphological cleanup — remove small noise blobs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    stats['steps_applied'].append('morphological_cleanup')

    stats['processed_size'] = list(binary.shape[:2])

    # Save preprocessed image
    out_path = os.path.join(output_dir, f"{doc_id}_preprocessed.png")
    cv2.imwrite(out_path, binary)

    return out_path, stats


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _deskew(gray: np.ndarray):
    """Detect and correct skew angle using Hough lines."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                             minLineLength=100, maxLineGap=10)
    angle = 0.0
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angles.append(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angles:
            angle = np.median(angles)
            # Only correct if skew is significant
            if abs(angle) > 0.5:
                (h, w) = gray.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h),
                                      flags=cv2.INTER_CUBIC,
                                      borderMode=cv2.BORDER_REPLICATE)
    return gray, angle


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order corner points: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype='float32')
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left
    rect[2] = pts[np.argmax(s)]   # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply a bird's-eye-view perspective warp."""
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = max(int(widthA), int(widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxW - 1, 0],
        [maxW - 1, maxH - 1],
        [0, maxH - 1]
    ], dtype='float32')

    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxW, maxH))


def _perspective_transform(color_img: np.ndarray, gray: np.ndarray):
    """
    Detect the largest quadrilateral (document boundary) and warp it.
    Returns None if no clear document boundary is found.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    doc_contour = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx
            break

    if doc_contour is None:
        return None

    # Only apply if the document fills a reasonable portion of the image
    img_area = color_img.shape[0] * color_img.shape[1]
    doc_area = cv2.contourArea(doc_contour)
    if doc_area < 0.15 * img_area:
        return None

    return _four_point_transform(color_img, doc_contour.reshape(4, 2))
