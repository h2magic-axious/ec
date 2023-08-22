import base64
from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

random_generator = Random.new().read


class Encryptor:
    def __init__(self):
        self.rsa = RSA.generate(1024, random_generator)
        self.public = self.rsa.publickey().exportKey().decode()
        self.private = self.rsa.exportKey().decode()

    def encrypt(self, content: str):
        cipher = PKCS1_v1_5.new(self.rsa)
        return base64.b64encode(cipher.encrypt(content.encode())).decode()

    def decrypt(self, content: str):
        cipher = PKCS1_v1_5.new(self.rsa, random_generator)
        return cipher.decrypt(base64.b64decode(content), random_generator).decode()
