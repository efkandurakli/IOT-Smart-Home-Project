from flask import Flask, Response, jsonify
import cv2

app = Flask(__name__)


app = Flask(__name__)

def gen_frames():
    """Generates frames from the camera."""
    camera = cv2.VideoCapture(0)  # 0 for default camera

    while True:
        success, frame = camera.read()  # Read a frame from the camera

        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Returns the video feed as a stream."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/current_frame')
def get_current_frame():
    """Returns the current frame as a JPEG image."""
    camera = cv2.VideoCapture(0)
    success, frame = camera.read()
    if not success:
        return jsonify({'message': 'Could not read frame from camera'})

    ret, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = buffer.tobytes()

    return Response(frame_bytes, mimetype='image/jpeg')


if __name__ == '__main__':
    app.run(debug=True)


if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)

