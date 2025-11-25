from cryptography.fernet import Fernet

# Paste the key you received in the email here as a string
key = b'tQ1VvPuEY2p8nA7NPPJ5S5epkKiJ7l29EppJfYpswhc='

# Load the encrypted log file
with open("log_encrypted.txt", "rb") as f:
    encrypted_data = f.read()

cipher_suite = Fernet(key)
decrypted_data = cipher_suite.decrypt(encrypted_data)

# Print or save the decrypted log
print(decrypted_data.decode())

# Optionally, save to a file
with open("log_decrypted.txt", "w") as f:
    f.write(decrypted_data.decode())
