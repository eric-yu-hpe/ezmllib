from ezmllib.constants import FERNET_KEY_FILE

import os
import os.path
import logging, sys
from cryptography.fernet import Fernet
import pam
from pwd import getpwnam
import getpass


def is_pwd_available():
    """ Check if password is available for user
    """
    username = getpass.getuser().strip()
    pwd_file = "/home/" + username + "/.user_pwd"
    if os.path.exists(pwd_file):
        return True
    else:
        return False

def get_fernet_key():
    with open(FERNET_KEY_FILE, mode='rb') as f:
        ecrypt_decrypt_key = f.read()
    return ecrypt_decrypt_key

def get_password():
    """Get password of user
    """
    username = getpass.getuser().strip()
    try:
        pwd_file = "/home/" + username + "/.user_pwd"

        fernet = Fernet(get_fernet_key())
        with open(pwd_file, 'rb') as f:
            encrypted_pwd = f.read()
        password = fernet.decrypt(encrypted_pwd).decode('utf-8')
        return password
    except:
        if os.path.exists(pwd_file):
            os.remove(pwd_file)
        print('Failed to get encrypted password')

def save_password(password):
    """Save password of user
    """
    username = getpass.getuser().strip()
    try:
        pam_tester = pam.pam()
        is_valid_user = pam_tester.authenticate(username,password)
        if not is_valid_user:
            return ""
    except Exception as e:
        return ""
    try:
        pwd_file = "/home/" + username + "/.user_pwd"
        fernet = Fernet(get_fernet_key())
        pwd_encrypted = fernet.encrypt(password.encode("utf-8"))
        with open(pwd_file, 'wb') as f:
            f.write(pwd_encrypted)
        # get UIDs and GIDs
        uid = getpwnam(username)[2]
        gid = getpwnam(username)[3]
        # Change the ownership of password file to user.
        os.chown(pwd_file, uid, gid)
    except:
        print('Failed to save password')