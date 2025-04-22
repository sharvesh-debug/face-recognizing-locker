import time
import threading
import os
import cv2
import numpy as np
import face_recognition
import hardware
import face_recognition_utils
import telegram_bot
import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_directories():
    """Ensure required directories exist."""
    for directory in [config.KNOWN_FACES_PATH, config.UNKNOWN_FACES_PATH]:
        os.makedirs(directory, exist_ok=True)
    logging.info("Directories set up")

def initialize_camera():
    """Try initializing the camera with multiple attempts."""
    for attempt in range(3):
        camera = cv2.VideoCapture(config.CAMERA_ID)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        if camera.isOpened():
            ret, test_frame = camera.read()
            if ret and test_frame is not None:
                logging.info("Camera initialized successfully")
                return camera

        logging.warning(f"Camera initialization attempt {attempt + 1} failed")
        time.sleep(1)
        camera.release()

    raise Exception("Could not open camera after multiple attempts")

def process_frame(frame, database):
    """Process a frame for face recognition."""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")

    if not face_locations:
        return None, None

    largest_face = max(face_locations, key=lambda rect: (rect[2] - rect[0]) * (rect[1] - rect[3]))

    face_encodings = face_recognition.face_encodings(rgb_frame, [largest_face])
    if not face_encodings or not isinstance(face_encodings[0], np.ndarray) or face_encodings[0].size == 0:
        logging.warning("Face detected but encoding extraction failed.")
        return largest_face, None

    face_encoding = face_encodings[0]
    name = "Unknown"
    best_match_distance = float('inf')

    for person_name, known_encoding in database.items():
        if not isinstance(known_encoding, np.ndarray) or known_encoding.size == 0:
            logging.warning(f"Skipping invalid encoding for {person_name}")
            continue

        distances = face_recognition.face_distance([known_encoding], face_encoding)
        if distances.size > 0:
            face_distance = float(distances[0])
            if face_distance < best_match_distance and face_distance < config.FACE_CONFIDENCE_THRESHOLD:
                best_match_distance = face_distance
                name = person_name

    return largest_face, name

def main():
    """Main loop for face recognition door system."""
    try:
        logging.info("Starting Face Recognition Door System...")
        setup_directories()

        database = face_recognition_utils.load_face_database()
        if not database:
            logging.warning("No face encodings found in database")
        else:
            logging.info(f"Loaded {len(database)} faces into database")

        hardware.setup_gpio()
        camera = initialize_camera()
        telegram_bot.initialize_bot(database)

        logging.info("System initialized and ready")
        logging.info("Press Ctrl+C to exit")

        cooldown_period = 2
        last_detection_time = 0

        while True:
            ret, frame = camera.read()
            if not ret or frame is None or frame.shape[0] == 0 or frame.shape[1] == 0:
                logging.error("Camera error: Failed to capture valid image")
                time.sleep(1)
                continue

            current_time = time.time()
            if current_time - last_detection_time < cooldown_period:
                time.sleep(0.1)
                continue

            last_detection_time = current_time
            face_location, name = process_frame(frame, database)

            if face_location is None:
                logging.info("No face detected, waiting...")
                time.sleep(0.5)
                continue

            logging.info(f"Recognition result: {name}")

            if name != "Unknown":
                logging.info(f"Welcome, {name}! Unlocking the door.")
                threading.Thread(target=hardware.unlock_door, args=(config.UNLOCK_DURATION,), daemon=True).start()
            else:
                logging.info("Unknown face detected, sending alert")

                top, right, bottom, left = face_location
                face_img = frame[top:bottom, left:right]

                timestamp = int(time.time())
                face_path = os.path.join(config.UNKNOWN_FACES_PATH, f"unknown_{timestamp}.jpg")
                cv2.imwrite(face_path, face_img)

                threading.Thread(target=telegram_bot.send_unknown_face_alert, args=(face_path,), daemon=True).start()

            time.sleep(cooldown_period)

    except KeyboardInterrupt:
        logging.info("Exiting due to user interrupt")
    except Exception as e:
        logging.error(f"ERROR: {e}")
    finally:
        if camera and camera.isOpened():
            camera.release()
        hardware.cleanup()
        telegram_bot.shutdown_bot()
        logging.info("System shutdown complete")

if __name__ == "__main__":
    main()
