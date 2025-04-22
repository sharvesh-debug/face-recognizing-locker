import os
import time
import pickle
import cv2
import face_recognition
import numpy as np
import config

# Ensure directories exist
def setup_directories():
    """Create necessary directories if they don't exist"""
    os.makedirs(config.KNOWN_FACES_PATH, exist_ok=True)
    os.makedirs(config.UNKNOWN_FACES_PATH, exist_ok=True)
    print("Directories created/verified")

# Initialize face database
def load_face_database():
    """Load the face database or create a new one if it doesn't exist"""
    if os.path.exists(config.FACE_DATABASE_PATH):
        with open(config.FACE_DATABASE_PATH, 'rb') as f:
            database = pickle.load(f)
            print(f"Loaded face database with {len(database['names'])} faces")
            return database
    else:
        database = {"encodings": [], "names": []}
        print("Created new face database")
        return database

# Save face database
def save_face_database(database):
    """Save the face database to disk"""
    with open(config.FACE_DATABASE_PATH, 'wb') as f:
        pickle.dump(database, f)
    print("Face database saved")

# Initialize camera
def setup_camera():
    """Initialize the webcam"""
    camera = cv2.VideoCapture(config.CAMERA_ID)
    if not camera.isOpened():
        raise Exception("Failed to open webcam")
    
    # Set resolution
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    
    # Warm up the camera
    for _ in range(5):
        camera.read()
    
    print("Camera initialized")
    return camera

# Capture image
def capture_image(camera):
    """Capture an image from the webcam"""
    # Try to get a frame multiple times in case of errors
    for _ in range(5):
        ret, frame = camera.read()
        if ret and frame is not None and frame.size > 0:
            # Convert from BGR (OpenCV) to RGB (face_recognition)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return rgb_frame
        time.sleep(0.5)
    
    print("Failed to capture image from webcam")
    return None

# Add face to database
def add_face_to_database(database, face_encoding, name):
    """Add a face encoding to the database"""
    database["encodings"].append(face_encoding)
    database["names"].append(name)
    save_face_database(database)
    print(f"Added {name} to database")

# Recognize face
def recognize_face(image, database):
    """Recognize faces in an image"""
    if image is None:
        return "Camera error", None
    
    # Find all faces in the image
    face_locations = face_recognition.face_locations(image)
    
    if len(face_locations) == 0:
        return "No face detected", None
    
    # Use the first face found
    face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
    
    # Check if face is in database
    if len(database["encodings"]) > 0:
        # Calculate face distances
        face_distances = face_recognition.face_distance(database["encodings"], face_encoding)
        
        # Find the closest match
        best_match_index = np.argmin(face_distances)
        
        # If the best match is close enough, consider it a match
        if face_distances[best_match_index] < config.FACE_CONFIDENCE_THRESHOLD:
            return database["names"][best_match_index], None
    
    # If no match found, save the unknown face
    timestamp = int(time.time())
    face_image_path = f"{config.UNKNOWN_FACES_PATH}/unknown_{timestamp}.jpg"
    # Convert RGB back to BGR for saving
    cv2.imwrite(face_image_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    
    return "Unknown", face_image_path

# Save a known person's image
def save_known_person_image(image, name):
    """Save an image of a known person"""
    # Create a unique filename
    image_path = f"{config.KNOWN_FACES_PATH}/{name}.jpg"
    # Convert RGB back to BGR for saving
    cv2.imwrite(image_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    print(f"Saved image for {name}")
    return image_path
