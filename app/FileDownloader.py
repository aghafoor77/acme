import json
import logging
import os
import re


class FileDownloader:
    def __init__(self, BASE_DIR):
        # Allowed filenames to prevent serving arbitrary files
        self.ALLOWED_FILES = {
            "pm": "post-postman.json",
            "ev": "environment_variables.json",
        }
        # Configure logging
        self.BASE_DIR = (
            BASE_DIR  # os.getenv("ACME_DATA_DIR", "/path/to/your/uuid/directories")
        )
        logging.basicConfig(level=logging.INFO)
        # Secure UUID pattern (accepts 32 chars or standard UUID format)
        self.UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F\-]{36}$")

    def is_valid_uuid(self, uuid_value: str) -> bool:
        """Validate UUID format."""
        return bool(self.UUID_PATTERN.match(uuid_value))

    def safe_join(self, base, *paths):
        """
        Prevent directory traversal: all joined paths MUST remain inside base.
        """
        final_path = os.path.abspath(os.path.join(base, *paths))
        if not final_path.startswith(os.path.abspath(base)):
            raise ValueError("Unsafe path detected (directory traversal attempt).")
        return final_path

    def get_file_from_uuid(self, uuid_value: str, file_key: str):
        """
        Shared secure handler:
        - validate input
        - verify directory exists
        - verify file exists
        - prevent directory traversal
        - return the file securely
        """

        # 1. Validate UUID input
        if not self.is_valid_uuid(uuid_value):
            logging.warning(f"Invalid UUID format: {uuid_value}")
            return json.dumps({"error": "Invalid UUID format"}, indent=4), 400

        # 2. Validate file key
        if file_key not in self.ALLOWED_FILES:
            return json.dumps({"error": "Invalid file key"}), 400

        filename = self.ALLOWED_FILES[file_key]

        try:
            # 3. Build safe paths
            folder_path = self.safe_join(self.BASE_DIR, uuid_value)
            file_path = self.safe_join(folder_path, filename)
        except ValueError:
            logging.error(
                f"Directory traversal attempt detected for UUID: {uuid_value}"
            )
            return json.dumps({"error": "Invalid path"}, indent=4), 400

        # 4. Check directory existence
        if not os.path.isdir(folder_path):
            logging.info(f"UUID directory not found: {folder_path}")
            return json.dumps({"error": "UUID directory not found"}, indent=4), 404

        # 5. Check file existence
        if not os.path.isfile(file_path):
            logging.info(f"Required file not found: {file_path}")
            return json.dumps({"error": f"File '{filename}' not found"}, indent=4), 404

        # 6. Serve file securely
        logging.info(f"Serving file: {file_path}")
        return file_path


"""
@app.get("/pm/<uuid_value>")
def get_pm(uuid_value):
    return get_file_from_uuid(uuid_value, "pm")


@app.get("/ev/<uuid_value>")
def get_ev(uuid_value):
    return get_file_from_uuid(uuid_value, "ev")
"""
