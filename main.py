# main.py (Versão 4.0 - Final com correção do Event Loop)

import os
import uuid
import subprocess
import httpx
import asyncio  # <--- 1. IMPORTAÇÃO ADICIONADA
from flask import Flask, request, jsonify, Response
from sqlalchemy import create_engine, text

# --- Configuração Inicial ---
app = Flask(__name__ )
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url) if db_url else None

# --- Endpoint do Webhook (Nossa "Doca de Carga") ---
@app.route('/webhook/umbler', methods=['POST'])
def umbler_webhook():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "Nenhum dado recebido"}), 400
    numero_cliente = data.get('sender', {}).get('phone')
    primeira_mensagem = data.get('message', {}).get('body')
    nome_cliente = data.get('sender', {}).get('name')
    if not numero_cliente or not primeira_mensagem: return jsonify({"status": "error", "message": "Dados essenciais ausentes"}), 400
    try:
        with engine.connect() as connection:
            query_cliente = text("SELECT id FROM clientes WHERE telefone = :telefone")
            resultado = connection.execute(query_cliente, {"telefone": numero_cliente}).fetchone()
            cliente_id = None
            if resultado:
                cliente_id = resultado[0]
            else:
                novo_id_cliente = uuid.uuid4()
                adscode = "WPP" + str(uuid.uuid4())[:5].upper()
                nome_empresa = f"Lead WhatsApp ({nome_cliente or numero_cliente})"
                insert_cliente = text("INSERT INTO clientes (id, adscode, nome_empresa, nome_contato, telefone) VALUES (:id, :adscode, :nome_empresa, :nome_contato, :telefone)")
                connection.execute(insert_cliente, {"id": novo_id_cliente, "adscode": adscode, "nome_empresa": nome_empresa, "nome_contato": nome_cliente or "Não informado", "telefone": numero_cliente})
                cliente_id = novo_id_cliente
            insert_atendimento = text("INSERT INTO atendimentos (id, cliente_id, descricao, responsavel, status) VALUES (:id, :cliente_id, :descricao, :responsavel, :status)")
            connection.execute(insert_atendimento, {"id": uuid.uuid4(), "cliente_id": cliente_id, "descricao": f"Primeira mensagem: '{primeira_mensagem}'", "responsavel": "Não Atribuído", "status": "Aberto"})
            connection.commit()
    except Exception as e:
        print(f"ERRO NO WEBHOOK: {e}")
        return jsonify({"status": "error", "message": "Erro interno do servidor"}), 500
    return jsonify({"status": "success", "message": "Atendimento criado"}), 200


# --- SEÇÃO DO PROXY - COMPLETAMENTE SUBSTITUÍDA ---

STREAMLIT_URL = "http://127.0.0.1:8501"
client = httpx.AsyncClient(base_url=STREAMLIT_URL )

# 2. A FUNÇÃO AGORA É SÍNCRONA (SEM 'async' NA FRENTE DE 'def')
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def streamlit_proxy(path):
    """
    Este proxy síncrono envolve a chamada assíncrona com asyncio.run(),
    resolvendo o problema do 'event loop is closed'.
    """
    # 3. CRIAMOS UMA FUNÇÃO INTERNA ASSÍNCRONA
    async def do_request():
        try:
            # O código do proxy agora vive aqui dentro
            url = request.url.replace(request.host_url, STREAMLIT_URL + '/')
            headers = {key: value for key, value in request.headers if key.lower() != 'host'}

            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=request.get_data(),
                params=request.args,
                follow_redirects=False # Parâmetro que corrigimos anteriormente
            )
            return Response(response.content, response.status_code, response.headers.items())

        except httpx.ConnectError:
            return "A aplicação está iniciando, por favor aguarde e atualize a página em alguns segundos.", 503
        except Exception as e:
            return f"Erro no proxy: {e}", 500

    # 4. USAMOS asyncio.run( ) PARA EXECUTAR A FUNÇÃO INTERNA
    return asyncio.run(do_request())


# --- Comando para Iniciar a Aplicação ---
def run():
    # Inicia o Streamlit como um processo separado
    streamlit_command = "streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"
    subprocess.Popen(streamlit_command, shell=True)

    # Inicia o Flask na porta que o Render nos fornece
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    run()
