class AppError(Exception):
    def __init__(self, message:str, messageCode:str, statusCode:int = 500):
        super().__init__(message)
        self.message = message
        self.messageCode = messageCode
        self.statusCode = statusCode