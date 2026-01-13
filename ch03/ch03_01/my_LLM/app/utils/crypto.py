import bcrypt

def encrypt(secret):
    secretBytes = secret.encode('utf-8')
    salt = bcrypt.gensalt()
    hashedSecret = bcrypt.hashpw(secretBytes, salt)

    return hashedSecret.decode('utf-8')

def verify(secret, hashed):
    secretBytes = secret.encode('utf-8')
    hashedBytes = hashed.encode('utf-8')

    return bcrypt.checkpw(secretBytes, hashedBytes)
