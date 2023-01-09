from ezmllib.constants import FERNET_KEY_FILE

import logging
import os
import os.path
import sys
from cryptography.fernet import Fernet

encyption_logger = logging.getLogger("Encryption configuration")
encyption_logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
log_handler.setFormatter(formatter)
encyption_logger.addHandler(log_handler)

# Create Fernet key for encryption/decryption of password
def create_encrypt_decrypt_key():
    """Create Fernet key for encryption/decryption of password
    """
    ecrypt_decrypt_key = Fernet.generate_key()
    if not os.path.exists(FERNET_KEY_FILE):
        with open(FERNET_KEY_FILE, 'wb') as fertnet_key_file:
            fertnet_key_file.write(ecrypt_decrypt_key)

if __name__ == "__main__":
    try:
        create_encrypt_decrypt_key()
        encyption_logger.info("Created Fernet key for encryption/decryption")
    except:
        encyption_logger.error("Failed to create Fernet key for encryption/decryption")
        sys.exit(1)
