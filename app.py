from face_recognition_app.facial_recognition import *
from flask import *
from picamera2 import Picamera2

app = Flask(__name__)
picam2 = Picamera2()

def generate_frames():
    while True:
        #capture a frame from camera
        frame = picam2.capture_array()
        #process the frame with the function
        processed_frame = process_frame(frame)
        #draw text and boxes based on processed frame
        display_frame = draw_results(processed_frame)

        #process fps
        current_fps = calculate_fps()
        #attach fps counter
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        #encode frame as jpeg
        ret, buffer = cv2.imencode('.jpg', display_frame)
        if not ret:
            continue

        #yield from as mjpeg
        yield (b' --frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(buffer) + b'\r\n')

#@app.route("/login", methods=['POST'])
#def login():
#    print("Login")
#    return "Pressed"
	
@app.route('/')
def default():
    return render_template("index.html")

@app.route('/main')
def main():
    return render_template("main.html")

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug = True)

