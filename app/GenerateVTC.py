import json
import os

import yaml

AZURE_OPENAI_KEY = os.environ["AZURE_OPENAI_KEY"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]
AZURE_OPENAI_ENGINE = os.environ["AZURE_OPENAI_ENGINE"]


# OWASP Top 10 reference text
OWASP_TOP10 = """
OWASP Top 10:
1. Injection (SQL, NoSQL, OS, etc.)
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities (XXE)
5. Broken Access Control
6. Security Misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging & Monitoring
"""


def load_openapi(file_path):
    """Load OpenAPI spec from YAML or JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def extract_endpoints(openapi_spec):
    """Extract path and method information from OpenAPI spec."""
    endpoints = []
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                endpoints.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                    }
                )
    return endpoints


def generate_with_llm(prompt, client):
    """Generate text with GPT-4 given a prompt."""
    response = client.chat.completions.create(
        model=AZURE_OPENAI_ENGINE,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior security expert specializing in API testing. "
                    "Your job is to generate rigorous vulnerability test cases for REST APIs, "
                    "You provide the output in a ready-to-use Postman collection format "
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


def main():
    openapi_file = "app/myapi.yaml"  # Change to your OpenAPI file path

    # Load OpenAPI and extract endpoints
    openapi_spec = load_openapi(openapi_file)
    endpoints = extract_endpoints(openapi_spec)

    if not endpoints:
        print("No endpoints found in OpenAPI spec.")
        return

    # Generate tests for each endpoint

    for ep in endpoints:
        prompt = (
            f"{OWASP_TOP10}\n"
            f"Generate vulnerability test cases for following endpoint in postman format:\n"
            f"Method: {ep['method']}\n"
            f"Path: {ep['path']}\n"
            f"Summary: {ep['summary']}\n"
            f"Description: {ep['description']}\n"
            "List relevant security tests:\n"
        )

        print("=" * 80)
        print(f"Endpoint: {ep['method']} {ep['path']}")
        result = generate_with_llm(prompt, None)
        print(result)
        print("=" * 80)


if __name__ == "__main__":
    main()
