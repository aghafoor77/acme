from .OpenAPIParser import OpenAPIParser


def main():
    openapi_url = "https://petstore3.swagger.io/api/v3/openapi.json"
    print("OpenAPI URL:", openapi_url)
    parser = OpenAPIParser(openapi_url)
    parser.fetch_spec()
    print("Title:", parser.get_title())
    print("Endpoints med argument:")
    parameters = parser.get_parameters()
    for endpoint, params in parameters.items():
        print(f"{endpoint}:")
        if not params:
            print("  No parameters.")
        for p in params:
            print(
                f"  - {p['name']} ({p['in']}), type: {p['type']}, required: {p['required']}"
            )


if __name__ == "__main__":
    main()
