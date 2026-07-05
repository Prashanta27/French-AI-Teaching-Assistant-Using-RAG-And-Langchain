import hashlib
import json
import os

TRACKER_FILE = "data/indexed_files.json"


def calculate_file_hash(file_path):

    sha = hashlib.sha256()

    with open(file_path, "rb") as f:

        while True:

            chunk = f.read(8192)

            if not chunk:
                break

            sha.update(chunk)

    return sha.hexdigest()


def load_tracker():

    if not os.path.exists(TRACKER_FILE):
        return {}

    try:
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_tracker(data):

    with open(TRACKER_FILE, "w") as f:

        json.dump(data, f, indent=4)