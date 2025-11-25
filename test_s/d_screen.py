from cryptography.fernet import Fernet

# Paste the key you received in the email here as a string
key = b'CfxDlQFix3h4WrVFfRdHWjoKqyPXI9k1QNeH6Q9vh1M='

# Path to the encrypted screenshot file
encrypted_file_path = "/home/wasiemmanuela/Desktop/b (copy).tech/finished_btech/test_s/screenshot_20250608_183401.png.enc"

# Path to save the decrypted screenshot
decrypted_file_path = encrypted_file_path.replace(".enc", "")

cipher_suite = Fernet(key)

with open(encrypted_file_path, "rb") as f:
    encrypted_data = f.read()

decrypted_data = cipher_suite.decrypt(encrypted_data)

with open(decrypted_file_path, "wb") as f:
    f.write(decrypted_data)

print(f"Decrypted file saved as {decrypted_file_path}")
