import requests


class OpenAPIParser:
    def __init__(self, url):
        self.url = url
        self.spec = None

    def fetch_spec(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            self.spec = response.json()
        except Exception as e:
            raise RuntimeError(f"Failed fetching the OpenAPI specification.: {e}")

    def get_paths(self):
        if self.spec is None:
            raise RuntimeError(
                "The specification hasn't been fetched yet. Call fetch_spec first.!"
            )
        return self.spec.get("paths", {})

    def get_endpoints(self):
        if self.spec is None:
            raise RuntimeError(
                "The specification hasn't been fetched yet. Call fetch_spec first.!"
            )
        endpoints = []
        for path, methods in self.spec.get("paths", {}).items():
            for method in methods:
                endpoints.append((method.upper(), path))
        return endpoints

    def get_title(self):
        if self.spec is None:
            raise RuntimeError(
                "The specification hasn't been fetched yet. Call fetch_spec first.!"
            )
        return self.spec.get("info", {}).get("title", "No title was found.")

    def get_parameters(self):
        if self.spec is None:
            raise RuntimeError(
                "The specification hasn't been fetched yet. Call fetch_spec first.!"
            )
        params = {}
        for path, methods in self.spec.get("paths", {}).items():
            for method, operation in methods.items():
                endpoint_key = f"{method.upper()} {path}"
                all_params = operation.get("parameters", [])
                # Kolla även efter path-level parameters
                if "parameters" in methods:
                    all_params += methods["parameters"]
                param_list = []
                for p in all_params:
                    pname = p.get("name")
                    ptype = None
                    if "schema" in p:
                        ptype = p["schema"].get("type")
                    param_list.append(
                        {
                            "name": pname,
                            "in": p.get("in"),
                            "type": ptype,
                            "required": p.get("required", False),
                        }
                    )
                params[endpoint_key] = param_list
        return params
