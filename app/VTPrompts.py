class VTPrompts:
    def __init__(self):
        self._head_prompt = {
            "API1:2023": "Broken Object Level Authorization",
            "API2:2023": "Broken Authentication",
            "API3:2023": "Broken Object Property Level Authorization",
            "API4:2023": "Unrestricted Resource Consumption",
            "API5:2023": "Broken Function Level Authorization",
            "API6:2023": "Unrestricted Access to Sensitive Business Flows",
            "API7:2023": "Server Side Request Forgery",
            "API8:2023": "Security Misconfiguration",
            "API9:2023": "Improper Inventory Management",
            "API10:2023": "Unsafe Consumption of APIs",
        }

    def create_prompt_for_newman_script(self, endpoint, selectedvulernabilities):
        concatenatedvulernabilities = "'".join(selectedvulernabilities.values())
        print(concatenatedvulernabilities)

        prompt = (
            f"{concatenatedvulernabilities}, and edge/corner payloads\n"
            f"Automatic looping through payloads in one request\n"
            f"Pre-request & test scripts for injection safety, response time, and anomaly detection\n"
            f"Logging anomalies (500 errors, slow responses, sensitive info leaks)\n"
            f"Exporting anomalies into testReport environment variable\n"
            f"Be ready to run with Newman for automated JSON report generation.\n"
            f"{endpoint}\n"
        )
        return prompt

    def create_prompt_for_postman(self, endpoint, selectedvulernabilities):
        concatenatedvulernabilities = ", ".join(selectedvulernabilities.values())
        """prompt = (
            f"Reset context — let’s start over. Consider {concatenatedvulernabilities}, and edge/corner payloads\n"
            f"Create a Postman collection (produce valid json and do not use any function like repeat in the output text) with rigorous vulnerability test cases for this API endpoint. Each test should be clearly labeled and URL-encoded where needed.\n"
            f"Include edge and corner cases like invalid types, very large/small numbers, negitive and positive numbers and special characters\n"
            f"Automatically identify all dynamic values (e.g., path parameters, query parameters, request body fields) that need to be configurable, such as base URL, authentication tokens, user IDs, emails, passwords, verification codes, roles, org numbers, etc., and define them as Postman environment variables.\n"
            f"Use {{variable_name}} placeholders in requests wherever a dynamic value is required\n"
            f"{endpoint}\n)"""
        prompt = (
            f"Reset context. Given OWASP Top 10 API vulnerabilities: {concatenatedvulernabilities} and endpoint: {endpoint}, generate a valid Postman collection JSON with these rules:\n"
            f"- Include edge/corner cases: invalid types, very large/small numbers, negative/positive numbers, special characters, empty values\n"
            f"- Create environment variables only for required dynamic elements:\n"
            f"  - Authentication tokens (valid & invalid)\n"
            f"  - Identifiers or ids\n"
            f"- For request body, generate vulnerability-focused payloads; do not create variables unless mandatory\n"
            f"- Use {{variable_name}} placeholders for dynamic values\n"
            f"- URL-encode paths where needed\n"
            f"- Provide a separate Postman environment JSON with only detected dynamic variables and example values, ready to import\n"
        )
        return prompt


def main():
    # openapi_file = "./app/shortopenapi.yaml"  # Replace with your file path
    vtPrompts = VTPrompts()
    ep = """{
    "delete": {
        "tags": [
            "vc-issuance-controller"
        ],
        "operationId": "deleteGuest",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": true,
                "schema": {
                    "type": "integer",
                    "format": "int32"
                }
            }
        ],
        "responses": {
            "200": {
                "description": "default response",
                "content": {
                    "*/*": {
                        "schema": {
                            "type": "object"
                        }
                    }
                }
            }
        }
    }
}"""

    print(vtPrompts.create_prompt_for_postman(ep, vtPrompts._head_prompt))


if __name__ == "__main__":
    main()
