class MessageDto:

    def __init__(self, message_id: str, message_body: str):
        self.message_id = message_id
        self.message_body = message_body

    def __str__(self):
        return f'{{"message_id": {self.message_id}, "message_body": {self.message_body}}}'
