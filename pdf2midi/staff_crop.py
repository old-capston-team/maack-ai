import cv2
import time

idx = 3

def click_event(event, x, y, flags, params):
    global idx
    if event == cv2.EVENT_LBUTTONDOWN:
        w, h = params["width"], params["height"]
        top_left_x = max(0, x - w // 2)
        top_left_y = max(0, y - h // 2)
        cropped_image = img[top_left_y:top_left_y + h, top_left_x:top_left_x + w]
        cv2.imwrite(f"crop/staff{idx}.png", cropped_image)
        idx += 1

img = cv2.imread("2.png")
cv2.imshow("image", img)

params = {"width":6, "height":170}
cv2.setMouseCallback("image", click_event, params)

cv2.waitKey(0)
cv2.destroyAllWindows()