import os

SECONDARY_ADDRESSES = os.getenv("SECONDARY_ADDRESSES").split(",") if "SECONDARY_ADDRESSES" in os.environ else ["localhost:50051"]