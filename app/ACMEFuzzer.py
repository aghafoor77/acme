import json
import random
import string
import warnings

from faker import Faker
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.errors import NonInteractiveExampleWarning
from hypothesis.strategies import data
from OpenAPIHandler import OpenAPIHandler

warnings.filterwarnings("ignore", category=NonInteractiveExampleWarning)


class ACMEFuzzer:
    def __init__(self):
        self.fake = Faker()
        self.openapi = None

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

    def draw_example_from_strategy(self, strategy):
        """Safely draw an example without NonInteractiveExampleWarning."""

        @given(data())
        @settings(max_examples=1)
        def _inner(d):
            nonlocal result
            result = d.draw(strategy)

        result = None
        _inner()  # run hypothesis once
        return result

    # ------------------------------
    # Build Postman Collection
    # ------------------------------
    def build_collection(self, paths):
        postman_items = []
        for path, methods in paths.items():
            for method, details in methods.items():
                path = path.split(":", 1)[1].strip()

                request_url = path

                # Generate multiple fuzzed cases per parameter set
                fuzzed_cases = []

                # Collect parameter schemas
                params = details.get("parameters", [])
                body_schema = None
                if "requestBody" in details:
                    content = details["requestBody"].get("content", {})
                    if content:
                        keys = list(content.keys())
                        if len(keys) > 0:
                            body_schema = content[keys[0]].get("schema", {})

                # Check if security header required
                security = []
                if "security" in details:
                    secoption = details["security"]
                    for item in secoption:
                        if "bearerAuth" in item:
                            security.append("bearerAuth")
                        if "basicAuth" in item:
                            security.append("basicAuth")
                # Generate fuzz cases (max 5 variations per endpoint)

                for _ in range(5):
                    request = {
                        "method": method.upper(),
                        "header": [],
                        "url": {
                            "raw": request_url,
                            "host": [request_url],
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
                    ops = method.upper()
                    if (
                        ops == "PUT"
                        or ops == "POST"
                        or ops == "PATCH"
                        or ops == "DELETE"
                    ):
                        if body_schema:
                            component = self.extract_req_component_schema(
                                body_schema, details
                            )
                            if component is not None:
                                # ---------------------------------------------

                                payload_strategy = self.strategy_from_schema(component)
                                if payload_strategy is not None:
                                    fuzzed_body = payload_strategy.example()
                                    # =============================================
                                    # fuzzed_body = random.choice(self.fuzz_value(component))
                                    request["body"] = {
                                        "mode": "raw",
                                        "raw": json.dumps(fuzzed_body),
                                        "options": {"raw": {"language": "json"}},
                                    }

                    # Postman already have full path in host attribute
                    request["url"]["path"] = []
                    # Check security content as well

                    header = [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "type": "text",
                        }
                    ]
                    for item in security:
                        if "bearerAuth" == item:
                            secheader = [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{fuzz_auth_token_valid}}",
                                    "type": "text",
                                }
                            ]
                            header.extend(secheader)

                        if "basicAuth" == item:
                            secheader = [
                                {
                                    "key": "Authorization",
                                    "value": "Basic {{fuzz_auth_base64}}",
                                    "type": "text",
                                }
                            ]
                            header.extend(secheader)
                    request["header"] = header

                    fuzzed_cases.append(
                        {"name": f"FUZZ - {ops} {path}", "request": request}
                    )

                postman_items.extend(fuzzed_cases)

        return postman_items

    def strategy_from_schema(self, schema):
        if not schema or "type" not in schema:
            raise ValueError("Invalid schema")

        t = schema["type"]
        if t == "object":
            props = {}
            for k, v in schema.get("properties", {}).items():
                if v["type"] == "string":
                    props[k] = st.text()
                elif v["type"] == "integer":
                    props[k] = st.integers()
                elif v["type"] == "boolean":
                    props[k] = st.booleans()
                else:
                    # fallback for unhandled types
                    props[k] = st.none()
            return st.fixed_dictionaries(props)

        elif t == "array":
            item_strategy = self.strategy_from_schema(schema["items"])
            return st.lists(item_strategy)

        elif t == "string":
            return st.text()

        elif t == "integer":
            return st.integers()

        elif t == "boolean":
            return st.booleans()

        else:
            # fallback for unknown types
            return st.none()

    # ------------------------------
    # Main Function
    # ------------------------------
    def fuzz_openapi(self):
        self.load_openapi()
        # return self.build_collection()

    def extract_req_component_schema(self, requested, details):
        comp = details["components"]
        if comp:
            schemas = comp["schemas"]
            if schemas:
                keys = list(schemas.keys())
                req_comp = requested["$ref"]
                result = req_comp.rsplit("/", 1)[-1]
                if result in keys:
                    obj = schemas[result]
                    return obj
        return None


# ------------------------------
# Usage Example
# ------------------------------
if __name__ == "__main__":
    openapi_file = (
        "/home/chaincode/Desktop/acmeimp/microsecai/input/updatemedicalreport.yaml"
    )
    fuzzer = ACMEFuzzer()
    openAPIHandler = OpenAPIHandler(openapi_file)
    endpoints = openAPIHandler.get_endpoints()
    paths = {}
    for p in endpoints:
        paths[p["path"]] = p["endpoint"]
    print(json.dumps(fuzzer.build_collection(paths), indent=4))
