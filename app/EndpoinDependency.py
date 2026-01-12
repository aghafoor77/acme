import json

# Ultra-complete CRUD / operation order
crud_order = [
    "create",
    "add",
    "insert",
    "store",
    "register",
    "signup",
    "new",
    "init",
    "setup",
    "build",
    "provision",
    "read",
    "get",
    "find",
    "fetch",
    "list",
    "search",
    "query",
    "retrieve",
    "view",
    "details",
    "info",
    "summary",
    "update",
    "edit",
    "modify",
    "patch",
    "put",
    "change",
    "merge",
    "revise",
    "replace",
    "correct",
    "adjust",
    "delete",
    "remove",
    "destroy",
    "revoke",
    "cancel",
    "archive",
    "clear",
    "purge",
    "drop",
    "disable",
    "deactivate",
    "export",
    "export-csv",
    "export-all",
    "download",
    "download-csv",
    "report",
    "generate-report",
    "backup",
    "login",
    "logout",
    "auth",
    "authenticate",
    "token",
    "refresh",
    "verify-token",
    "session",
    "signin",
    "signout",
    "role",
    "permission",
    "access",
    "authorize",
    "grant",
    "revoke",
    "policy",
    "security",
    "approve",
    "reject",
    "activate",
    "deactivate",
    "submit",
    "process",
    "complete",
    "finalize",
    "start",
    "stop",
    "sanitize",
    "validate",
    "deserialize",
    "serialize",
    "encode",
    "decode",
    "normalize",
    "transform",
    "convert",
    "notify",
    "send",
    "message",
    "alert",
    "email",
    "sms",
    "push",
    "webhook",
    "broadcast",
    "signal",
    "check",
    "ping",
    "health",
    "status",
    "configuration",
    "settings",
    "config",
    "metrics",
    "logs",
    "history",
    "process-file",
    "process-data",
    "calculate",
    "compute",
    "aggregate",
    "analyze",
    "evaluate",
]

# List of common IDs used for dependencies
dependency_keys = ["id", "userId", "reportId", "token", "sessionId", "pid"]


def extract_dependencies(endpoint):
    """Inspect requestBody and parameters to find fields that are likely consumed/produced"""
    dependencies = set()
    # Parameters
    for param in endpoint.get("parameters", []):
        name = param.get("name")
        if name and name.lower() in dependency_keys:
            dependencies.add(name.lower())
    # Request Body schema
    req_body = endpoint.get("requestBody", {}).get("content", {})
    for media_type in req_body.values():
        schema = media_type.get("schema", {})
        if "$ref" in schema:
            # Could parse ref, for now we just assume it contains dependencies
            dependencies.update(
                [
                    k.lower()
                    for k in schema.get("properties", {}).keys()
                    if k.lower() in dependency_keys
                ]
            )
        elif "properties" in schema:
            dependencies.update(
                [
                    k.lower()
                    for k in schema["properties"].keys()
                    if k.lower() in dependency_keys
                ]
            )
    return dependencies


def generate_execution_sequence(openapi_file):
    with open(openapi_file) as f:
        spec = json.load(f)

    endpoints = []
    produced_keys = set()  # Keep track of IDs that have been produced
    execution_sequence = []

    # Flatten all endpoints
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            endpoints.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "details": details,
                    "dependencies": extract_dependencies(details),
                    "order": None,
                    "matched": False,
                }
            )

    # Step 1: Auth endpoints first
    for ep in endpoints:
        details = ep["details"]
        tags = details.get("tags", [])
        op_id = details.get("operationId", "").lower()
        summary = details.get("summary", "").lower()
        if (
            any("auth" in tag.lower() for tag in tags)
            or "login" in op_id
            or "login" in summary
        ):
            ep["order"] = 0
            execution_sequence.append(ep)
            ep["matched"] = True
            # If token produced, mark it
            produced_keys.add("token")

    # Step 2: Dependency-aware ordering
    remaining = [ep for ep in endpoints if not ep["matched"]]

    while remaining:
        progressed = False
        for ep in remaining:
            # If all dependencies are already produced or no dependencies, we can execute
            if not ep["dependencies"] or ep["dependencies"].issubset(produced_keys):
                # Determine order by crud_order keyword
                op_id = ep["details"].get("operationId", "").lower()
                summary = ep["details"].get("summary", "").lower()
                for i, keyword in enumerate(crud_order):
                    if (
                        keyword in op_id
                        or keyword in summary
                        or keyword in ep["method"].lower()
                    ):
                        ep["order"] = i + 1
                        break
                if ep["order"] is None:
                    ep["order"] = len(crud_order) + 1

                # Add to sequence
                execution_sequence.append(ep)
                ep["matched"] = True
                # Assume endpoint produces IDs in request/response
                produced_keys.update(ep["dependencies"])
                progressed = True
        if not progressed:
            # Circular dependency or unknown fields, just add remaining
            for ep in remaining:
                if not ep["matched"]:
                    ep["order"] = len(crud_order) + 2
                    execution_sequence.append(ep)
                    ep["matched"] = True
            break
        remaining = [ep for ep in endpoints if not ep["matched"]]

    # Print final execution sequence
    for i, ep in enumerate(execution_sequence, start=1):
        step_name = (
            ep["details"].get("summary")
            or ep["details"].get("operationId")
            or f"{ep['method']} {ep['path']}"
        )
        print(f"{i}. {step_name}")
        print(f"   {ep['method']} {ep['path']}")
        if ep["dependencies"]:
            print(f"   Dependencies: {', '.join(ep['dependencies'])}")
        print("")


if __name__ == "__main__":
    file_path = "/home/chaincode/Desktop/acmeimp/microsecai/input/temp.yaml"  # replace with your OpenAPI JSON/YAML
    generate_execution_sequence(file_path)
