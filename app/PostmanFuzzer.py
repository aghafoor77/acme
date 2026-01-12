import json
import random
import string

from faker import Faker
from hypothesis import strategies as st


class PostmanFuzzer:
    def __init__(self, openapi_file: str):
        self.openapi_file = openapi_file
        self.fake = Faker()
        self.openapi = None

    def load_openapi(self):
        with open(self.openapi_file, "r", encoding="utf-8") as f:
            self.openapi = json.load(f)

    # ------------------------------
    # Fuzzing Strategies
    # ------------------------------
    def fuzz_string_values(self):
        """Combine Faker + Hypothesis string strategies"""
        return [
            self.fake.name(),
            self.fake.email(),
            "".join(random.choices(string.ascii_letters, k=10)),
            "",
            "🔥💀🚀",
            "A" * 1000,
            st.text().example(),  # Hypothesis edge-case string
        ]

    def fuzz_number_values(self):
        """Combine random + Hypothesis int strategies"""
        return [
            -1,
            0,
            1,
            2147483647,
            -2147483648,
            random.randint(-999999999, 999999999),
            st.integers().example(),  # Hypothesis edge int
            st.floats(allow_nan=False, allow_infinity=False).example(),
        ]

    def fuzz_boolean_values(self):
        return [True, False, st.booleans().example()]

    def fuzz_value(self, schema):
        """Pick multiple fuzzed values based on schema type"""
        if not schema or "type" not in schema:
            return self.fuzz_string_values()

        t = schema["type"]
        if t == "string":
            return self.fuzz_string_values()
        elif t in ["integer", "number"]:
            return self.fuzz_number_values()
        elif t == "boolean":
            return self.fuzz_boolean_values()
        elif t == "array":
            return [
                [v] for v in self.fuzz_value(schema.get("items", {"type": "string"}))
            ]
        elif t == "object":
            return [
                {
                    k: random.choice(self.fuzz_value(v))
                    for k, v in schema.get("properties", {}).items()
                }
            ]
        else:
            return self.fuzz_string_values()

    # ------------------------------
    # Build Postman Collection
    # ------------------------------
    def build_collection(self):
        base_url = self.openapi.get("servers", [{}])[0].get("url", "{{baseUrl}}")
        paths = self.openapi.get("paths", {})

        postman_items = []

        for path, methods in paths.items():
            for method, details in methods.items():
                request_url = base_url + path

                # Generate multiple fuzzed cases per parameter set
                fuzzed_cases = []

                # Collect parameter schemas
                params = details.get("parameters", [])
                body_schema = None
                if "requestBody" in details:
                    content = details["requestBody"].get("content", {})
                    if "application/json" in content:
                        body_schema = content["application/json"].get("schema", {})

                # Generate fuzz cases (max 5 variations per endpoint)
                for _ in range(5):
                    request = {
                        "method": method.upper(),
                        "header": [],
                        "url": {
                            "raw": request_url,
                            "host": [base_url],
                            "path": [p for p in path.strip("/").split("/") if p],
                        },
                    }

                    # Path & query parameters
                    for param in params:
                        fuzzed_val = random.choice(
                            self.fuzz_value(param.get("schema", {"type": "string"}))
                        )
                        if param["in"] == "path":
                            request["url"]["path"] = [
                                str(fuzzed_val) if p.strip("{}") == param["name"] else p
                                for p in request["url"]["path"]
                            ]
                        elif param["in"] == "query":
                            if "query" not in request["url"]:
                                request["url"]["query"] = []
                            request["url"]["query"].append(
                                {"key": param["name"], "value": str(fuzzed_val)}
                            )

                    # Request body fuzzing
                    if body_schema:
                        fuzzed_body = random.choice(self.fuzz_value(body_schema))
                        request["body"] = {
                            "mode": "raw",
                            "raw": json.dumps(fuzzed_body),
                            "options": {"raw": {"language": "json"}},
                        }

                    fuzzed_cases.append(
                        {
                            "name": f"{method.upper()} {path} (fuzzed)",
                            "request": request,
                        }
                    )

                postman_items.extend(fuzzed_cases)

        return postman_items

    # ------------------------------
    # Main Function
    # ------------------------------
    def fuzz_openapi(self):
        self.load_openapi()
        return self.build_collection()


# ------------------------------
# Usage Example
# ------------------------------
if __name__ == "__main__":
    fuzzer = PostmanFuzzer("./app/myapi.yaml")
    fuzzer.fuzz_openapi()
