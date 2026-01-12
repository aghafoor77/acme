import json
import logging
import os
from datetime import datetime

import yaml
from openapi_spec_validator import validate_spec

# from openapi_spec_validator.exceptions import OpenAPIValidationError


# Configure JSON audit logging
class JSONAuditLogger(logging.LoggerAdapter):
    """
    Logger adapter to output JSON formatted logs with user/action metadata.
    """

    def process(self, msg, kwargs):
        return json.dumps(msg), kwargs


logger = logging.getLogger("openapi_audit")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("openapi_handler_audit.json")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(message)s")  # raw message (JSON)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class OpenAPIHandler:
    """
    Professional OpenAPI file handler with JSON-formatted audit logging.
    """

    def __init__(self, openapi_file: str):
        """
        Initialize OpenAPIHandler.

        :param openapi_file: Path to OpenAPI file (.yaml, .yml, or .json)
        """
        self.openapi_file = openapi_file
        self.abs_path = os.path.abspath(openapi_file)
        self.data = None
        self.paths = {}
        self.parsed_paths = []

        self._log_audit(
            "initialize", f"Initialized OpenAPIHandler for file {self.abs_path}"
        )

    def _log_audit(self, action: str, details: str, user: str = "system"):
        """
        Log audit events in JSON format.

        :param action: Action performed (load, validate, parse, access)
        :param details: Additional information about the action
        :param user: User performing the action
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "user": user,
            "action": action,
            "details": details,
        }
        logger.info(log_entry)

    def _load_file(self):
        """Load OpenAPI file content into memory (JSON or YAML)."""
        ext = os.path.splitext(self.openapi_file)[1].lower()
        if not os.path.exists(self.openapi_file):
            self._log_audit(
                "load_file", f"File not found: {self.abs_path}", user="system"
            )
            raise FileNotFoundError(f"OpenAPI file not found: {self.abs_path}")

        with open(self.openapi_file, "r", encoding="utf-8") as f:
            if ext in [".yaml", ".yml"]:
                self.data = yaml.safe_load(f)
            elif ext == ".json":
                self.data = json.load(f)
            else:
                self._log_audit(
                    "load_file", f"Unsupported file format: {ext}", user="system"
                )
                raise ValueError(
                    f"Unsupported file format: {ext}. Use .json or .yaml/.yml"
                )

        self._log_audit(
            "load_file", f"Successfully loaded OpenAPI file: {self.abs_path}"
        )

    def _validate_file(self):
        """Validate OpenAPI file for required fields and strict compliance."""
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in self.data:
                self._log_audit("validate_file", f"Missing required field: {field}")
                raise ValueError(f"Invalid OpenAPI file: Missing field '{field}'")

        try:
            validate_spec(self.data)
            self._log_audit("validate_file", "OpenAPI file validation successful")
        except Exception as e:
            self._log_audit("validate_file", f"Unexpected validation error: {e}")
            raise

    def _parse_openapi(self):
        """
        Parse OpenAPI file to extract endpoints and their details.
        """
        self._load_file()
        self._validate_file()
        base_url = ""
        servers = self.data.get("servers", {})
        if servers is not None and len(servers) > 0:
            base_url = servers[0]["url"]
        components = self.data.get("components", {})

        self.paths = self.data.get("paths", {})
        self.parsed_paths = []

        for path, methods in self.paths.items():
            for method, details in methods.items():
                schemas = self.extract_schemas(components, details)
                ach_new = {"schemas": schemas}
                details["components"] = ach_new
                entry = {
                    "path": f"{method.upper()}: {base_url}{path}",
                    "endpoint": {method: details},
                }
                self.parsed_paths.append(entry)

        self._log_audit("parse_file", f"Parsed {len(self.parsed_paths)} endpoints")

    def extract_schemas(self, components, details):
        keys = details.keys()
        keys_list = list(keys)
        ret_schema = {}
        if "requestBody" in keys_list:
            requestBody = details["requestBody"]
            refs = self.extract_refs(requestBody, refs=None)
            if refs is not None and len(refs) > 0:
                ret_obj = self.extract_schema_object(components, refs[0])
                keys = ret_obj.keys()
                for k in keys:
                    ret_schema[k] = ret_obj[k]

        if "responses" in keys_list:
            responses = details["responses"]
            refs = self.extract_refs(responses, refs=None)
            if refs is not None and len(refs) > 0:
                ret_obj = self.extract_schema_object(components, refs[0])
                keys = ret_obj.keys()
                for k in keys:
                    ret_schema[k] = ret_obj[k]
        return ret_schema

    def extract_schema_object(self, components, refs):
        schemas = components.get("schemas", {})
        obj = {}
        for schema_name, schema_obj in schemas.items():
            last_part = refs.split("/")[-1]
            if last_part == schema_name:
                obj[schema_name] = schema_obj
        return obj

    def extract_refs(self, obj, refs=None):
        if refs is None:
            refs = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref":
                    refs.append(value)
                else:
                    self.extract_refs(value, refs)
        elif isinstance(obj, list):
            for item in obj:
                self.extract_refs(item, refs)
        return refs

    def get_endpoints(self, user: str = "system"):
        """
        Get all parsed endpoints and log access.

        :param user: User requesting access
        :return: List of endpoint dictionaries
        """
        if not self.parsed_paths:
            self._parse_openapi()

        self._log_audit(
            "access_endpoints",
            f"Accessed {len(self.parsed_paths)} endpoints",
            user=user,
        )

        return self.parsed_paths


def main():
    """Example usage of OpenAPIHandler."""
    openapi_file = "./input/useropenapi.yaml"
    handler = OpenAPIHandler(openapi_file)

    try:
        endpoints = handler.get_endpoints(user="admin_user")
        for entry in endpoints:
            print(f"Path: {entry['path']}")
            print("Endpoint:")
            print(json.dumps(entry["endpoint"], indent=4))
            print("=" * 80)
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "ERROR",
                    "user": "admin_user",
                    "action": "process_file",
                    "details": str(e),
                }
            )
        )
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
