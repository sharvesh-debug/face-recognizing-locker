import RPi.GPIO as GPIO
import time
import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Disable GPIO warnings
GPIO.setwarnings(False)

def setup_gpio():
    """Initialize GPIO pins for relay control."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.RELAY_PIN, GPIO.OUT)
    GPIO.output(config.RELAY_PIN, GPIO.HIGH)  # Start with door locked
    logging.info("GPIO initialized: Door locked")

def unlock_door(duration=None):
    """Unlock the door for a specified duration."""
    if duration is None:
        duration = config.UNLOCK_DURATION

    logging.info("Unlocking door...")
    GPIO.output(config.RELAY_PIN, GPIO.LOW)  # Activate relay (Unlock)
    time.sleep(duration)
    GPIO.output(config.RELAY_PIN, GPIO.HIGH)  # Deactivate relay (Lock)
    logging.info("Door locked again")

def cleanup():
    """Clean up GPIO resources."""
    GPIO.cleanup()
    logging.info("GPIO cleaned up")
