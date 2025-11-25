import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

def decrypt_aes_cbc(encrypted_file_path, decrypted_file_path, b64_key, b64_iv):
    """
    Decrypts a file encrypted with AES-256 in CBC mode with PKCS7 padding.
    """
    try:
        # Decode the base64-encoded key and IV to raw bytes
        key = base64.b64decode(b64_key)
        iv = base64.b64decode(b64_iv)

        # Read the encrypted data from the file
        with open(encrypted_file_path, 'rb') as encrypted_file:
            encrypted_data = encrypted_file.read()

        # Create a Cipher object configured for AES-256 CBC decryption
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

        # Create a decryptor object from the cipher
        decryptor = cipher.decryptor()

        # Decrypt the encrypted data
        padded_plaintext = decryptor.update(encrypted_data) + decryptor.finalize()

        # Create an unpadder object to remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()

        # Remove the padding to get the original plaintext
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

        # Write the decrypted plaintext to the output file
        with open(decrypted_file_path, 'wb') as decrypted_file:
            decrypted_file.write(plaintext)

        print(f"Decryption successful! Decrypted file saved as: {decrypted_file_path}")

    except Exception as error:
        print(f"An error occurred during decryption: {error}")

# Call the function with your specific parameters
decrypt_aes_cbc(
    encrypted_file_path="/home/wasiemmanuela/Desktop/b (copy).tech/finished_btech/test_a/recording_20250608_192826.wav.enc",  # Path to your encrypted file
    decrypted_file_path="/home/wasiemmanuela/Desktop/b (copy).tech",    # Output file path
    b64_key="Up13c/2Vm7c9lOwsOesm7K53BGiEenIffMJUvo1rbrs=",                     # Replace with your base64-encoded AES key
    b64_iv="akyOgv7iBmDFh+rcRO4hMg=="                          # Replace with your base64-encoded IV
)