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


# =========================
# HEALTHCHECK
# =========================

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "config-api"}), 200


# =========================
# GET CONFIG
# =========================

@app.route("/config/<guild_id>", methods=["GET"])
def get_config(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro", "msg": "Não autorizado"}), 401

    config = load_json(CONFIG_FILE)
    return jsonify(config.get(str(guild_id), {})), 200


# =========================
# SAVE CONFIG
# =========================

@app.route("/config/<guild_id>", methods=["POST"])
def save_config(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro", "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "erro", "msg": "Nenhum dado recebido"}), 400

    config = load_json(CONFIG_FILE)
    config[str(guild_id)] = data
    save_json(CONFIG_FILE, config)

    return jsonify({"status": "ok"}), 200


# =========================
# APPLY PANEL
# Esta rota salva a config e notifica o bot via webhook local se disponível.
# O bot (config_api.py interno) é quem realmente envia o painel no Discord.
# Aqui garantimos que a config foi salva e retornamos ok para o painel web.
# =========================

@app.route("/apply-panel/<guild_id>", methods=["POST"])
def apply_panel(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro", "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    gif_url = data.get("gif_url")

    # Carrega config atual do servidor
    config = load_json(CONFIG_FILE)
    guild_config = config.get(str(guild_id), {})

    if not guild_config:
        return jsonify({
            "status": "erro",
            "msg": "Configuração do servidor não encontrada. Configure os canais primeiro."
        }), 400

    # Salva gif_url na config se foi enviado
    if gif_url:
        guild_config["gif_url"] = gif_url
        config[str(guild_id)] = guild_config
        save_json(CONFIG_FILE, config)

    # Tenta acionar o bot via webhook interno (porta 5001) se BOT_WEBHOOK_URL estiver configurado
    bot_webhook = os.getenv("BOT_WEBHOOK_URL", "").rstrip("/")
    bot_token = os.getenv("CONFIG_API_TOKEN", "")

    if bot_webhook:
        try:
            import requests as req_lib
            resp = req_lib.post(
                f"{bot_webhook}/apply-panel/{guild_id}",
                headers={
                    "Authorization": f"Bearer {bot_token}",
                    "Content-Type": "application/json"
                },
                json={"gif_url": gif_url} if gif_url else {},
                timeout=25
            )
            if resp.status_code == 200:
                return jsonify({"status": "ok", "msg": "Painel enviado com sucesso pelo bot!"}), 200
            else:
                return jsonify({
                    "status": "erro",
                    "msg": f"Bot retornou {resp.status_code}: {resp.text[:200]}"
                }), 500
        except Exception as e:
            return jsonify({
                "status": "erro",
                "msg": f"Não foi possível contatar o bot: {str(e)}"
            }), 500

    # Se BOT_WEBHOOK_URL não está configurado, apenas confirma que a config foi salva
    # O painel será enviado na próxima vez que o bot reiniciar ou o admin usar /config_wl
    return jsonify({
        "status": "ok",
        "msg": "Configuração salva. Use /config_wl no Discord > 'Enviar Painel' para publicar no canal."
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
