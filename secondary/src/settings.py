import os

REPLICATION_DELAY_SEC = int(os.getenv("REPLICATION_DELAY_SEC")) if "REPLICATION_DELAY_SEC" in os.environ else None