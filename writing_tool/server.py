from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request, send_from_directory

from writing_tool.store import Store


WEB_DIR = Path(__file__).parent / "web"


def create_app(store: Store) -> Flask:
    app = Flask(__name__)

    @app.after_request
    def cors(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    def _to_sigma(graph: dict[str, Any]) -> dict[str, Any]:
        nodes = [
            {
                "key": f"n{n['id']}",
                "label": n["label"],
                "type": n.get("type", "note"),
                "attributes": n.get("props", {}),
            }
            for n in graph["nodes"]
        ]
        edges = [
            {
                "key": f"e{e['id']}",
                "source": f"n{e['source_id']}",
                "target": f"n{e['target_id']}",
                "label": e["label"],
            }
            for e in graph["edges"]
        ]
        return {"nodes": nodes, "edges": edges}

    @app.route("/api/graph")
    def api_graph() -> Response:
        g = {"nodes": store.all_nodes(), "edges": store.all_edges()}
        return jsonify(_to_sigma(g))

    @app.route("/api/graph/<path:label>")
    def api_subgraph(label: str) -> Response:
        nodes = store.find_nodes(label)
        if not nodes:
            return jsonify({"nodes": [], "edges": []})
        g = store.get_graph(nodes[0]["id"], depth=2)
        return jsonify(_to_sigma(g))

    @app.route("/api/stats")
    def api_stats() -> Response:
        return jsonify(store.stats())

    @app.route("/api/query", methods=["POST"])
    def api_query() -> Response:
        data = request.get_json(silent=True) or {}
        question = data.get("question", "")
        if not question:
            return jsonify({"answer": "No question provided."})
        from litellm import completion
        stats = store.stats()
        context = f"Graph has {stats['nodes']} nodes, {stats['edges']} edges. Types: {stats['by_type']}."
        resp = completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a story graph assistant. Answer concisely based on graph data."},
                {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
            ],
            temperature=0.3,
        )
        return jsonify({"answer": resp.choices[0].message.content})

    @app.route("/")
    def index() -> Response:
        if WEB_DIR.is_dir():
            return send_from_directory(str(WEB_DIR), "index.html")
        from flask import make_response
        return make_response("<h1>wt graph viewer</h1><p>No web/index.html found.</p>")

    return app
