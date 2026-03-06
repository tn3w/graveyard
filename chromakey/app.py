import os
from flask import Flask
from chromakey import Chromakey, chromakey


def load_dotenv(env_file=".env"):
    """Load environment variables from a .env file into os.environ."""
    if not os.path.exists(env_file):
        return

    with open(env_file, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = [x.strip() for x in line.split("=", 1)]
            os.environ[key] = value.strip("\"'")


load_dotenv()

app = Flask(__name__)

import logging

logging.basicConfig(level=logging.DEBUG)

auth = Chromakey(app)


@app.route("/")
@chromakey()
def hello_world():
    return "<html>Hello, World!</html>"


if __name__ == "__main__":
    app.run(debug=True)
