import json

import networkx as nx

TOKEN_FIELD_NAMES = {
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "jwt",
    "auth_token",
    "sessionid",
    "session_id",
}
ID_LIKE_SUFFIXES = ("id", "_id", "uuid", "_uuid")


def load_spec(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def node_id(method, path):
    return f"{method.upper()} {path}"


def extract_schema_fields(schema, spec):
    fields = set()
    if not schema or not isinstance(schema, dict):
        return fields
    if "$ref" in schema and schema["$ref"].startswith("#/"):
        ref_path = schema["$ref"].lstrip("#/").split("/")
        node = spec
        for p in ref_path:
            node = node.get(p, {})
        if node is not schema:
            fields |= extract_schema_fields(node, spec)
        return fields
    props = schema.get("properties", {})
    if isinstance(props, dict):
        for prop_name, prop_schema in props.items():
            fields.add(prop_name)
            fields |= extract_schema_fields(prop_schema, spec)
    if "items" in schema:
        fields |= extract_schema_fields(schema["items"], spec)
    for comb in ("allOf", "anyOf", "oneOf"):
        if comb in schema and isinstance(schema[comb], list):
            for subs in schema[comb]:
                fields |= extract_schema_fields(subs, spec)
    return fields


def get_request_fields(operation_obj, spec):
    fields = set()
    rb = operation_obj.get("requestBody", {})
    content = rb.get("content", {})
    for media in content.values():
        schema = media.get("schema", {})
        fields |= extract_schema_fields(schema, spec)
    for param in operation_obj.get("parameters", []):
        name = param.get("name")
        if name:
            fields.add(name)
    return fields


def get_response_fields(operation_obj, spec):
    fields = set()
    for status, resp in operation_obj.get("responses", {}).items():
        content = resp.get("content", {})
        for media in content.values():
            schema = media.get("schema", {})
            fields |= extract_schema_fields(schema, spec)
    return fields


def looks_like_token_field(name):
    if not name:
        return False
    ln = name.lower()
    if ln in TOKEN_FIELD_NAMES:
        return True
    if "token" in ln or "jwt" in ln or ln.endswith("id_token"):
        return True
    return False


class OpenApiExecPlanner:
    def __init__(self, openapi_path, out_json="execution_sequence.json"):
        self.spec = load_spec(openapi_path)
        self.graph = nx.DiGraph()
        self.out_json = out_json
        self.global_security = self.spec.get("security")
        self.security_schemes = self.spec.get("components", {}).get(
            "securitySchemes", {}
        )

    def extract_endpoints(self):
        for path, methods in self.spec.get("paths", {}).items():
            for method, details in methods.items():
                node = node_id(method, path)
                self.graph.add_node(node, method=method.upper(), path=path, op=details)

    def detect_auth_producers_and_protected(self):
        auth_producers = set()
        protected_nodes = set()
        # Map protected node -> required header/query
        self.protected_headers = {}

        for node in list(self.graph.nodes):
            meta = self.graph.nodes[node]
            op = meta.get("op", {})
            tags = [t.lower() for t in op.get("tags", []) if isinstance(t, str)]
            opid = (op.get("operationId") or "").lower()
            summary = (op.get("summary") or "").lower()
            hint_auth = (
                any("auth" in t or "login" in t or "token" in t for t in tags)
                or "login" in opid
                or "login" in summary
                or "auth" in opid
            )
            resp_fields = get_response_fields(op, self.spec)
            produces_token_field = any(looks_like_token_field(f) for f in resp_fields)
            if hint_auth or produces_token_field:
                auth_producers.add(node)

            # Determine if protected
            op_security = op.get("security", None)
            if op_security is None:
                if self.global_security:
                    protected_nodes.add(node)
                    self.protected_headers[node] = self.get_required_headers(
                        self.global_security
                    )
            else:
                if isinstance(op_security, list) and len(op_security) > 0:
                    protected_nodes.add(node)
                    self.protected_headers[node] = self.get_required_headers(
                        op_security
                    )
        return auth_producers, protected_nodes

    def get_required_headers(self, security_list):
        """
        Given a list of security requirements (operation.security or global security),
        return the list of headers/query params expected to satisfy it.
        """
        headers = set()
        for sec_req in security_list:
            for sec_name in sec_req.keys():
                scheme = self.security_schemes.get(sec_name, {})
                typ = scheme.get("type")
                if typ == "http" and scheme.get("scheme") == "bearer":
                    headers.add(scheme.get("name") or "Authorization")
                elif typ == "apiKey":
                    # name can be in header, query, or cookie
                    headers.add(scheme.get("name") or "X-API-KEY")
        return list(headers)

    def build_schema_dependencies(self):
        nodes = list(self.graph.nodes)
        for a in nodes:
            a_op = self.graph.nodes[a]["op"]
            a_resp_fields = get_response_fields(a_op, self.spec)
            for b in nodes:
                if a == b:
                    continue
                b_meta = self.graph.nodes[b]
                b_op = b_meta["op"]
                path = b_meta["path"]
                path_params = [
                    seg[1:-1]
                    for seg in path.split("/")
                    if seg.startswith("{") and seg.endswith("}")
                ]
                b_req_fields = set([p for p in path_params if p])
                b_req_fields.update(get_request_fields(b_op, self.spec))
                if a_resp_fields & b_req_fields:
                    self.graph.add_edge(a, b, reason="schema-field")

    def add_auth_edges(self, auth_producers, protected_nodes):
        for protected in protected_nodes:
            incoming = set(self.graph.predecessors(protected))
            if incoming & auth_producers:
                continue
            for auth in auth_producers:
                self.graph.add_edge(auth, protected, reason="auth")

    def compute_order(self):
        if nx.is_directed_acyclic_graph(self.graph):
            return list(nx.topological_sort(self.graph)), []
        else:
            cycles = list(nx.simple_cycles(self.graph))
            return list(nx.topological_sort(self.graph)), cycles

    def save_json(self, order, cycles, out_path=None):
        out = out_path or self.out_json
        data = {
            "status": "ok" if not cycles else "cycle_detected",
            "sequence": order if order else [],
            "cycles": cycles,
            "nodes": list(self.graph.nodes),
            "edges": [
                {"from": u, "to": v, "reason": self.graph.edges[u, v].get("reason")}
                for u, v in self.graph.edges
            ],
            "protected_headers": getattr(self, "protected_headers", {}),
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return out

    def run(self):
        self.extract_endpoints()
        auth_producers, protected_nodes = self.detect_auth_producers_and_protected()
        self.build_schema_dependencies()
        self.add_auth_edges(auth_producers, protected_nodes)
        order, cycles = self.compute_order()
        out_path = self.save_json(order, cycles)
        print(f"Nodes: {len(self.graph.nodes)} Edges: {len(self.graph.edges)}")
        print(
            f"Auth producers detected: {len(auth_producers)} Protected endpoints: {len(protected_nodes)}"
        )
        print(f"Execution sequence saved to {out_path}")
        return order, cycles


# ---------- CLI ----------
if __name__ == "__main__":
    file_path = "/home/chaincode/Desktop/acmeimp/microsecai/input/temp.yaml"  # replace with your OpenAPI JSON/YAML
    openapi_path = file_path
    out_json = (
        "/home/chaincode/Desktop/acmeimp/microsecai/input/execution_sequence.json"
    )
    planner = OpenApiExecPlanner(openapi_path, out_json)
    planner.run()
