# fix-protocol-simulator\src\fix_simulator\protocol\fix_message.py

from dataclasses import dataclass


@dataclass
class FixMessage:
    fields: dict

    def get(self, tag):
        return self.fields.get(tag)

    def set(self, tag, value):
        self.fields[tag] = value

    def encode(self):
        body = "\x01".join(f"{k}={v}" for k, v in self.fields.items())
        return body + "\x01"
