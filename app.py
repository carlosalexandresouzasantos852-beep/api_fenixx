from flask import Flask, request, jsonify
import json
import os
import asyncio
from threading import Thread

import discord

app = Flask(__name__)

CONFIG_FILE = "config.json"
API_TOKEN = os.getenv("CONFIG_API_TOKEN", "troque_esse_token")

BOT_INSTANCE = None


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


def attach_bot(bot):
    global BOT_INSTANCE
    BOT_INSTANCE = bot
    print("✅ Bot anexado à Config API")


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "config-api"}), 200


@app.route("/config/<guild_id>", methods=["GET"])
def get_config(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro", "msg": "Não autorizado"}), 401

    config = load_json(CONFIG_FILE)
    return jsonify(config.get(str(guild_id), {})), 200


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


async def _apply_panel_async(guild_id: int, gif_url: str = None):
    if BOT_INSTANCE is None:
        raise RuntimeError("Bot não anexado à Config API")

    config = load_json(CONFIG_FILE)
    guild_config = config.get(str(guild_id))

    if not guild_config:
        raise RuntimeError("Configuração do servidor não encontrada")

    guild = BOT_INSTANCE.get_guild(int(guild_id))
    if guild is None:
        raise RuntimeError("Bot não encontrou o servidor")

    canal_id = guild_config.get("painel")
    if not canal_id:
        raise RuntimeError("Canal do painel não configurado")

    canal = guild.get_channel(int(canal_id))
    if canal is None:
        raise RuntimeError("Canal do painel não encontrado")

    from cogs.whitelist import PainelView

    embed = discord.Embed(
        title="📋 PAINEL DE WHITELIST",
        description="Clique no botão abaixo para iniciar sua whitelist.",
        color=discord.Color.orange()
    )

    if gif_url:
        embed.set_image(url=gif_url)

    await canal.send(embed=embed, view=PainelView(BOT_INSTANCE, gif_url))


@app.route("/apply-panel/<guild_id>", methods=["POST"])
def apply_panel(guild_id):
    if not is_authorized(request):
        return jsonify({"status": "erro", "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    gif_url = data.get("gif_url")

    if BOT_INSTANCE is None:
        return jsonify({"status": "erro", "msg": "Bot não anexado à API"}), 500

    try:
        future = asyncio.run_coroutine_threadsafe(
            _apply_panel_async(int(guild_id), gif_url),
            BOT_INSTANCE.loop
        )
        future.result(timeout=20)

        return jsonify({"status": "ok", "msg": "Painel aplicado com sucesso"}), 200

    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


def run_config_api():
    port = int(os.getenv("CONFIG_API_PORT", 5001))
    app.run(host="0.0.0.0", port=port)


def start_config_api(bot=None):
    if bot is not None:
        attach_bot(bot)

    thread = Thread(target=run_config_api, daemon=True)
    thread.start()
    print("✅ Config API iniciada")