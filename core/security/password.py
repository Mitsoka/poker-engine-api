from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")


def hash_pwd(password: str):
    context = pwd_context.hash(password)
    return context
    

def verify_pwd(plain_password: str, hashed_password: str):
    result = pwd_context.verify(plain_password, hashed_password)
    return result