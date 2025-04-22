# Configuration settings for the face recognition door system

# Telegram settings
TELEGRAM_BOT_TOKEN = "7994803716:AAEJ1X1yXYIOUcy-gBtnfTlDMSVRic4pzhA"
ADMIN_CHAT_ID = "7049016318"

# Hardware settings
RELAY_PIN = 17  # GPIO pin for relay
UNLOCK_DURATION = 10  # Seconds to keep door unlocked

# Face recognition settings
FACE_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for face recognition
FACE_DATABASE_PATH = "database/face_database.pkl"
KNOWN_FACES_PATH = "database/known_faces"
UNKNOWN_FACES_PATH = "unknown_faces"

# Camera settings
CAMERA_ID = 0  # Default webcam
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

