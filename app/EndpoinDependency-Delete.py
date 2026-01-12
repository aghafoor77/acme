import json
import os
from collections import defaultdict

import networkx as nx
import yaml
from pyvis.network import Network


class OpenAPIDependencyInferer:
    def __init__(self, openapi_file, verbose=False):
        self.openapi_file = openapi_file
        self.verbose = verbose
        self.openapi = self._load_openapi()
        self.endpoints = {}  # (method, path) -> metadata
        self.edges = defaultdict(lambda: {"evidence": [], "count": 0})

        self._parse_openapi()

    def _load_openapi(self):
        with open(self.openapi_file, "r", encoding="utf-8") as f:
            raw = f.read()
        try:
            return json.loads(raw)
        except Exception:
            return yaml.safe_load(raw)

    def _resolve_ref(self, ref: str):
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        current = self.openapi
        try:
            for p in parts:
                current = current[p]
            return current
        except Exception:
            return None

    def _parse_openapi(self):
        paths = self.openapi.get("paths", {})
        for path, methods in paths.items():
            for method, md in methods.items():
                meth = method.upper()
                key = (meth, path)
                metadata = {
                    "responses": md.get("responses", {}),
                    "operationId": md.get("operationId"),
                    "links": {},
                    "schemas": [],
                }
                for status, resp in (md.get("responses") or {}).items():
                    resp_obj = (
                        self._resolve_ref(resp.get("$ref")) if "$ref" in resp else resp
                    )
                    if not resp_obj:
                        continue
                    # collect links
                    metadata["links"].update(resp_obj.get("links") or {})
                    # collect schema $ref
                    for content in (resp_obj.get("content") or {}).values():
                        schema = content.get("schema")
                        if schema and "$ref" in schema:
                            metadata["schemas"].append(schema["$ref"])
                self.endpoints[key] = metadata

        if self.verbose:
            print("Parsed OpenAPI endpoints:")
            for k, v in self.endpoints.items():
                print(k, v)

    def _evidence_score(self, evidence_list):
        # simple scoring: count unique evidence types
        return min(1.0, len(set(evidence_list)) / 3)

    def infer(self):
        """Infer dependencies based on OpenAPI links and schemas."""
        endpoints = list(self.endpoints.keys())
        for i, prod_key in enumerate(endpoints):
            for cons_key in endpoints:
                if prod_key == cons_key:
                    continue
                ev = []
                # 1) link evidence
                prod_meta = self.endpoints[prod_key]
                cons_meta = self.endpoints[cons_key]
                for link in prod_meta.get("links", {}).values():
                    opid = link.get("operationId")
                    if opid and cons_meta.get("operationId") == opid:
                        ev.append("openapi_link")
                # 2) schema reference evidence
                cons_params = cons_meta.get("schemas") or []
                prod_schemas = prod_meta.get("schemas") or []
                if any(c in prod_schemas for c in cons_params):
                    ev.append("schema_reference")
                if ev:
                    edge_key = (
                        f"{prod_key[0]} {prod_key[1]}",
                        f"{cons_key[0]} {cons_key[1]}",
                    )
                    self.edges[edge_key]["evidence"].extend(ev)
                    self.edges[edge_key]["count"] += 1

        # format results
        results = []
        for (a, b), meta in self.edges.items():
            results.append(
                {
                    "from": a,
                    "to": b,
                    "count": meta["count"],
                    "evidence": list(set(meta["evidence"])),
                    "confidence": round(self._evidence_score(meta["evidence"]), 2),
                }
            )
        return results

    def export_json(self, edges, outpath):
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump({"edges": edges}, f, indent=2, ensure_ascii=False)

    def export_html(self, edges, outpath):
        """
        Export the inferred OpenAPI dependency graph as an interactive HTML file.
        - Hierarchical layout (left → right)
        - Nodes grouped by top-level path prefix
        - Larger canvas for readability
        """
        G = nx.DiGraph()
        for e in edges:
            a = e["from"]
            b = e["to"]
            title = f"confidence={e.get('confidence')} evidence={e.get('evidence')}"
            G.add_node(a)
            G.add_node(b)
            G.add_edge(a, b, title=title, weight=e.get("count", 1))

        # Create PyVis network
        net = Network(directed=True, height="1200px", width="100%", notebook=False)
        # Use physics + hierarchical layout
        net.barnes_hut()
        net.set_options(
            """
        var options = {
        "layout": {
            "hierarchical": {
            "enabled": true,
            "direction": "LR",
            "sortMethod": "directed"
            }
        },
        "physics": {
            "hierarchicalRepulsion": {
            "nodeDistance": 250
            },
            "minVelocity": 0.75
        }
        }
        """
        )

        # Add nodes with group based on top-level path
        for n, data in G.nodes(data=True):
            # Extract top-level path for grouping (e.g., "/users")
            try:
                path = n.split(" ", 1)[1]  # remove method
                prefix = (
                    path.strip("/").split("/")[0] if "/" in path else path.strip("/")
                )
                group = prefix if prefix else "root"
            except Exception:
                group = "root"
            net.add_node(n, label=n, title=n, shape="box", group=group)

        # Add edges
        for u, v, data in G.edges(data=True):
            net.add_edge(
                u, v, value=data.get("weight", 1), title=data.get("title"), arrows="to"
            )

        # Save interactive HTML
        net.show(outpath, notebook=False)


# ----------------- Example usage -----------------
def main():
    # Specify your OpenAPI file and output directory here
    # --- Specify your files here ---
    openapi_file = "/home/chaincode/Desktop/acmeimp/microsecai/dep/req_useropenapi.yaml"  # <-- change this to your OpenAPI file
    output_dir = "/home/chaincode/Desktop/acmeimp/microsecai/dep"  # <-- change this to your desired output folder
    os.makedirs(output_dir, exist_ok=True)

    inferer = OpenAPIDependencyInferer(openapi_file, verbose=True)
    edges = inferer.infer()

    json_path = os.path.join(output_dir, "edges.json")
    html_path = os.path.join(output_dir, "graph.html")

    inferer.export_json(edges, json_path)
    inferer.export_html(edges, html_path)

    print(f"JSON edges written to: {json_path}")
    print(f"Interactive HTML graph written to: {html_path}")


if __name__ == "__main__":
    main()
