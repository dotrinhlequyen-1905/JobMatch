"""pgvector persistence with a JSON adapter for isolated SQLite tests.

The bytes interface preserves the trained model and existing ML script contracts.
Production stores native vectors, rather than bytea blobs or a process-local index.
"""

import numpy as np
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import JSON, Float
from sqlalchemy.types import TypeDecorator


class Embedding(TypeDecorator):
    impl = VECTOR
    cache_ok = True

    class comparator_factory(TypeDecorator.Comparator):
        def cosine_distance(self, vector):
            return self.op("<=>", return_type=Float)(vector)

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(JSON() if dialect.name == "sqlite" else VECTOR())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray, memoryview)):
            value = np.frombuffer(value, dtype=np.float32)
        return np.asarray(value, dtype=np.float32).tolist()

    def process_result_value(self, value, dialect):
        return None if value is None else np.asarray(value, dtype=np.float32).tobytes()
