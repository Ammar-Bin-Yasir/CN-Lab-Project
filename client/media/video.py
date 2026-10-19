"""Small JPEG frames for LAN video; no OpenCV display windows."""

import time
from queue import Full


def capture(stop, outgoing, preview, error):
    camera = None
    try:
        import cv2

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            raise RuntimeError(
                "Camera unavailable. Check permissions or use voice call."
            )
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        while not stop.is_set():
            started = time.monotonic()
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Camera stopped delivering frames.")
            frame = cv2.resize(frame, (320, 240))
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if ok:
                data = encoded.tobytes()
                preview(data)
                try:
                    outgoing.put_nowait(b"\x02" + data)
                except Full:
                    pass
            stop.wait(max(0, 0.1 - (time.monotonic() - started)))
    except Exception as exc:
        error(str(exc))
    finally:
        if camera is not None:
            camera.release()
