import hashlib


class GenerateCode:

    def generate_code(self, str=None):
        code = hashlib.md5(str.encode()).hexdigest()
        return code
