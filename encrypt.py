from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


class Encryptor:
    __algorithm = hashes.SHA256()
    __padding = padding.OAEP(
        mgf=padding.MGF1(algorithm=__algorithm),
        algorithm=__algorithm,
        label=None
    )

    def __init__(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        self.public_key = self.private_key.public_key()

    def encrypt(self, context: str):
        return self.public_key.encrypt(context.encode(), self.__padding)

    def decrypt(self, context):
        return self.private_key.decrypt(bytes.fromhex(context), self.__padding)

    def serialize(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
