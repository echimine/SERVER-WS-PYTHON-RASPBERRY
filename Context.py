# machine à etat qui suivant si prod ou dev on change l'url en ws ou wss
class Context:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def url(self):
        return f"ws://{self.host}:{self.port}"

    @staticmethod
    def dev():
        return Context("192.168.1.12", 8765)
    
    # @staticmethod
    # def prod():
    #     return Context("192.168.10.127", 9000)

    @staticmethod
    def prod():
        return Context("172.28.55.77", 9000)
    
