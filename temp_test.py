import os
import cv2
import time

# Disable hardware transforms for Media Foundation backend
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

def main():
    stream_url = "http://192.168.2.131:8080/video"
    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("Failed to open the stream. Check the URL or network connection.")
        return

    retry_count = 0
    max_retries = 5  # Maximum number of retries for stream reconnection

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame. Retrying...")
            retry_count += 1
            if retry_count > max_retries:
                print("Maximum retries reached. Exiting...")
                break
            time.sleep(2)  # Wait before retrying
            cap.release()
            cap = cv2.VideoCapture(stream_url)  # Reinitialize the stream
            continue

        retry_count = 0  # Reset retry count on successful frame read
        cv2.imshow("Stream Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()