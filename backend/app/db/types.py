import json

from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.types import TypeDecorator


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class JSONText(TypeDecorator):
    """Store Python dict/list values as JSON text across supported databases."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)
