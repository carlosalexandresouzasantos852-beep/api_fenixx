from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

CONFIG_FILE = "config.json"
API_TOKEN = os.getenv("CONFIG_API_TOKEN")

if not API_TOKEN:
    raise RuntimeError("CONFIG_API_TOKEN não configurado")


def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def is_authorized(req):
    auth = req.headers.get("Authorization", "")
    return auth == f"Bearer {API_TOKEN}"


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/config/<guild_id>", methods=["GET"])
def get_config(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro"}), 401

    config = load_json(CONFIG_FILE)
    return jsonify(config.get(str(guild_id), {}))


@app.route("/config/<guild_id>", methods=["POST"])
def save_config(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro"}), 401

    data = request.get_json()

    config = load_json(CONFIG_FILE)
    config[str(guild_id)] = data
    save_json(CONFIG_FILE, config)

    return jsonify({"status": "ok"})