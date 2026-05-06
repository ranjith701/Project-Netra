import cv2

rtsp_url = "rtsp://c3-lab:Aura%24em1@192.168.0.200:554/stream1"

cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    cv2.imshow("Tapo RTSP", frame)

    if cv2.waitKey(1) == 27:  # ESC key
        break

cap.release()
cv2.destroyAllWindows()