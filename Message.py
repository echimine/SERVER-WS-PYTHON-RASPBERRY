import json


class _EnvoiTypes:
    TEXT        = "ENVOI_TEXT"
    IMAGE       = "ENVOI_IMAGE"
    AUDIO       = "ENVOI_AUDIO"
    VIDEO       = "ENVOI_VIDEO"
    SENSOR      = "ENVOI_SENSOR"
    CLIENT_LIST = "ENVOI_CLIENT_LIST"


class _ReceptionTypes:
    TEXT        = "RECEPTION_TEXT"
    IMAGE       = "RECEPTION_IMAGE"
    AUDIO       = "RECEPTION_AUDIO"
    VIDEO       = "RECEPTION_VIDEO"
    SENSOR      = "RECEPTION_SENSOR"
    CLIENT_LIST = "RECEPTION_CLIENT_LIST"


class _AdminTypes:
    ROUTING_LOG         = "ADMIN_ROUTING_LOG"
    CLIENT_CONNECTED    = "ADMIN_CLIENT_CONNECTED"
    CLIENT_DISCONNECTED = "ADMIN_CLIENT_DISCONNECTED"
    CLIENT_LIST_FULL    = "ADMIN_CLIENT_LIST_FULL"


class MessageType:
    DECLARATION = "DECLARATION"
    SYS_MESSAGE = "SYS_MESSAGE"
    WARNING     = "WARNING"

    ENVOI     = _EnvoiTypes()
    RECEPTION = _ReceptionTypes()
    ADMIN     = _AdminTypes()


class Message:
    def __init__(self, message_type, emitter, receiver, value, sensor_id=None):
        self.message_type = message_type
        self.emitter      = emitter
        self.receiver     = receiver
        self.value        = value
        self.sensor_id    = sensor_id

    def to_json(self):
        payload = {
            "message_type": self.message_type,
            "data": {
                "emitter":   self.emitter,
                "receiver":  self.receiver,
                "value":     self.value,
                "sensor_id": self.sensor_id,
            }
        }
        return json.dumps(payload)

    @classmethod
    def from_json(cls, raw):
        parsed       = json.loads(raw)
        message_type = parsed.get("message_type")
        data         = parsed.get("data", {})
        return cls(
            message_type=message_type,
            emitter=data.get("emitter", ""),
            receiver=data.get("receiver", ""),
            value=data.get("value"),
            sensor_id=data.get("sensor_id"),
        )
