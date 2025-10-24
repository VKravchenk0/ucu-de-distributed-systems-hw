from dataclasses import dataclass

@dataclass
class MessageDto:
    previous_message_id: int
    message_id: int
    message_body: str
