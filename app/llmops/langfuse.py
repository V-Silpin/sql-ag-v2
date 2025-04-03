from langfuse.callback import CallbackHandler

import os
from dotenv import load_dotenv
load_dotenv()

secret_key = os.getenv("LANGFUSE_SECRET_KEY")
public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
host = os.getenv("LANGFUSE_HOST")

langfuse_handler=CallbackHandler(
        public_key=public_key,
        secret_key=secret_key,
        host=host
)