# import the necessary packages
import cv2
import numpy as np
import argparse
from skimage.filters import threshold_local
from imutils.perspective import four_point_transform
import imutils
from tkinter import filedialog, Tk

# Function to reorder points (top-left, top-right, bottom-right, bottom-left)
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

# GUI for selecting image
root = Tk()
root.withdraw()
path = filedialog.askopenfilename(title="Select Image to Scan")

if not path:
    print("No file selected.")
    exit()

# load the image and compute the ratio
image = cv2.imread(path)
ratio = image.shape[0] / 500.0
orig = image.copy()
image = imutils.resize(image, height=500)

# grayscale, blur and edge detection
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (5, 5), 0)
edged = cv2.Canny(gray, 75, 200)

# Step 1: Edge Detection
print("STEP 1: Edge Detection")
cv2.imshow("Image", image)
cv2.imshow("Edged", edged)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Find contours
cnts = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

# Detect screen contour
screenCnt = None
for c in cnts:
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02 * peri, True)
    if len(approx) == 4:
        screenCnt = approx
        break

# Fallback: if no 4-corner shape, use bounding box of largest contour
if screenCnt is None:
    print("Could not detect 4-corner document. Falling back to bounding rectangle...")
    largest_contour = cnts[0]
    x, y, w, h = cv2.boundingRect(largest_contour)
    screenCnt = np.array([
        [[x, y]],
        [[x + w, y]],
        [[x + w, y + h]],
        [[x, y + h]]
    ])

if screenCnt is None:
    print("Could not detect document corners.")
    exit()

# Step 2: Show detected contour
print("STEP 2: Find contours of paper")
cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 2)
cv2.imshow("Outline", image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# GUI-based manual editing
points = screenCnt.reshape(4, 2)
editing = True
selected_point = -1

# Mouse callback function for editing
def click_event(event, x, y, flags, param):
    global selected_point, points
    if event == cv2.EVENT_LBUTTONDOWN:
        for i, pt in enumerate(points):
            if np.linalg.norm(pt - np.array([x, y])) < 20:
                selected_point = i
                break
    elif event == cv2.EVENT_MOUSEMOVE and selected_point != -1:
        points[selected_point] = [x, y]
    elif event == cv2.EVENT_LBUTTONUP:
        selected_point = -1

cv2.namedWindow("Edit Corners")
cv2.setMouseCallback("Edit Corners", click_event)

while editing:
    clone = image.copy()
    for pt in points:
        cv2.circle(clone, tuple(pt.astype(int)), 5, (0, 0, 255), -1)
    cv2.polylines(clone, [points.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)
    cv2.imshow("Edit Corners", clone)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        editing = False
    elif key == 27:  # ESC key
        print("Editing cancelled.")
        cv2.destroyAllWindows()
        exit()

cv2.destroyAllWindows()
screenCnt = order_points(points)

# Step 3: Perspective transform
print("STEP 3: Apply perspective transform")
warped = four_point_transform(orig, screenCnt * ratio)
warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
T = threshold_local(warped, 11, offset=10, method="gaussian")
warped = (warped > T).astype("uint8") * 255

# Display results
cv2.imshow("Original", imutils.resize(orig, height=650))
cv2.imshow("Scanned", imutils.resize(warped, height=650))
cv2.waitKey(0)
cv2.destroyAllWindows()