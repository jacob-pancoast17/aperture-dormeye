import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import os
import requests
import datetime
import zoneinfo

def load_encodings():
    path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'encodings.pickle'
            )

    # Load pre-trained face encodings
    print("[INFO] loading encodings...")
    with open(path, "rb") as f:
        data = pickle.loads(f.read())
        print(data)
    global known_face_encodings, known_face_names
    known_face_encodings = data["encodings"]
    known_face_names = data["names"]

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1920, 1080)}))
picam2.start()

# Initialize our variables
cv_scaler = 4 # this has to be a whole number

face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0

current_faces = []
current_faces_count = 0
previous_count = 0
create_log = False

def process_frame(frame):
    global face_locations, face_encodings, face_names, current_faces, current_faces_count, previous_count, create_log
    create_log = False
    
    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
    
    # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
    
    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')
    
    face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        # New code
        if not known_face_encodings:
            face_names.append(name)
            continue    
        
        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)

        #if len(face_distance) > 0:
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]

        face_names.append(name)

        if name not in current_faces:
            current_faces.append(name)
    
    for name in current_faces:
        if name not in face_names:
            current_faces.remove(name)
    
    current_faces_count = len(current_faces)
    if (current_faces_count > previous_count):
        create_log = True
    
    previous_count = current_faces_count
    creating_log(create_log)

    return frame

def draw_results(frame):
    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler
        
        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        
        # Draw a label with a name below the face
        cv2.rectangle(frame, (left -3, top - 35), (right+3, top), (244, 42, 3), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)
    
    return frame

def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps

def generate_frames():
    while True:
        # Capture a frame from camera
        frame = picam2.capture_array()
    
        # Process the frame with the function
        processed_frame = process_frame(frame)
    
        # Get the text and boxes to be drawn based on the processed frame
        display_frame = draw_results(processed_frame)
    
        # Calculate and update FPS
        current_fps = calculate_fps()
    
        # Attach FPS counter to the text and boxes
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
        # Encode frame as a jpeg
        ret, buffer = cv2.imencode('.jpg', display_frame)
        byte_frame = buffer.tobytes()

        # Yield the frame as an mjpeg stream
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + byte_frame + b'\r\n')

def creating_log(create_log):
    if create_log:
        filename = datetime.datetime.now().strftime("%Y-%m-%d-%H.%M.%S.jpg")
        save = "log_photos/" + filename
        picam2.capture_file(save)
        print("picture taken")

        requests.post("http://localhost:5000/create_log", json={
            "faces": current_faces,
            "time": str(datetime.datetime.now().strftime("%Y-%m-%d   %I:%M:%S %p")),
            "photo_filename": filename
            })

if __name__ == "__main__":
    initialize()

