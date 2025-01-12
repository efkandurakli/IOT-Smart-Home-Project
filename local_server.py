from flask import Flask, Response, jsonify
import RPi.GPIO as GPIO
from time import sleep
from gpiozero import Buzzer
import cv2

GPIO.setmode(GPIO.BOARD)

GPIO.setup(13, GPIO.IN)
GPIO.setup(15, GPIO.IN)
GPIO.setup(16, GPIO.IN)
GPIO.setup(18, GPIO.OUT)

GPIO.output(18, GPIO.LOW)

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
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    success, frame = camera.read()
    if not success:
        return jsonify({'message': 'Could not read frame from camera'})

    ret, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = buffer.tobytes()
    camera.release()
    return Response(frame_bytes, mimetype='image/jpeg')

@app.route('/get_sensor_info')
def get_sensor_info():
    resp = {"Flamable": 0, "CO": 0, "Flame":0}

    if not GPIO.input(13):
        resp["Flamable"] = 1
    if not GPIO.input(15):
        resp["CO"] = 1
    if not GPIO.input(16):
        resp["Flame"] = 1

    return jsonify(resp)
@app.route('/set_alarm')
def set_alarm():
    count = 0
    while(count < 3):
        GPIO.output(18, GPIO.HIGH)
        sleep(1)
        GPIO.output(18, GPIO.LOW)
        sleep(1)
        count += 1
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)