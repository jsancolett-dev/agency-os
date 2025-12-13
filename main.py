# main.py (Versão 2.0 - Com Proxy Reverso para Streamlit)

import os
import uuid
import subprocess
import requests
from flask import Flask, request, jsonify, Response
from werkzeug.routing import Rule
from werkzeug.wrappers import Request
from sqlalchemy import create_engine, text

# --- Configuração Inicial ---
app = Flask(__name__)
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url) if db_url else None

# --- Endpoint do Webhook (Nossa "Doca de Carga") ---
# (Esta parte não mudou)
@app.route('/webhook/umbler', methods=['POST'])
def umbler_webhook():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Nenhum dado recebido"}), 400
    
    numero_cliente = data.get('sender', {}).get('phone')
    primeira_mensagem = data.get('message', {}).get('body')
    nome_cliente = data.get('sender', {}).get('name')

    if not numero_cliente or not primeira_mensagem:
        return jsonify({"status": "error", "message": "Dados essenciais ausentes"}), 400

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

# --- NOVA SEÇÃO: Proxy Reverso para o Streamlit ---
# Esta é a "ponte" que direciona o tráfego para a nossa loja (Streamlit)

STREAMLIT_URL = "http://127.0.0.1:8501"

@app.route('/', defaults={'path': ''} )
@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def streamlit_proxy(path):
    """
    Esta função intercepta TODAS as requisições que não são para o webhook
    e as repassa para o servidor Streamlit interno.
    """
    # Constrói a URL completa para o serviço Streamlit
    url = f"{STREAMLIT_URL}/{path}"
    
    # Repassa os cabeçalhos, dados, parâmetros, etc.
    headers = {key: value for (key, value) in request.headers if key != 'Host'}
    
    try:
        # Faz a requisição para o Streamlit
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True,
            params=request.args
        )

        # Retorna a resposta do Streamlit para o navegador do usuário
        # Isso inclui o conteúdo, o status e os cabeçalhos
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = [(name, value) for (name, value) in resp.raw.headers.items()
                        if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, resp_headers)
    
    except requests.exceptions.ConnectionError:
        # Se o Streamlit ainda não estiver pronto, mostra uma mensagem amigável
        return "A aplicação está iniciando, por favor aguarde e atualize a página em alguns segundos.", 503


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
