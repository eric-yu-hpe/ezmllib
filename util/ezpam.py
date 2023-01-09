import pam

def validate_user(user,pwd):
    """Validate user using pam
    """
    pam_tester = pam.pam()
    is_valid_user = pam_tester.authenticate(user,pwd)
    if not is_valid_user:
        print("Invalid Password, Please provide correct password")
        return False
    else:
        print("Valid user")
        return True