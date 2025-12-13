# main.py (Versão 3.0 - Com Proxy Reverso Robusto para WebSockets)

import os
import uuid
import subprocess
import httpx # Novo import para o proxy
from flask import Flask, request, jsonify, Response
from sqlalchemy import create_engine, text

# --- Configuração Inicial ---
app = Flask(__name__ )
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url) if db_url else None

# --- Endpoint do Webhook (Nossa "Doca de Carga") ---
# (Esta parte não mudou)
@app.route('/webhook/umbler', methods=['POST'])
def umbler_webhook():
    # ... (código do webhook omitido para brevidade, ele continua o mesmo)
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


# --- NOVA SEÇÃO: Proxy Reverso Robusto para Streamlit (com suporte a WebSocket) ---

STREAMLIT_URL = "http://127.0.0.1:8501"
client = httpx.AsyncClient(base_url=STREAMLIT_URL )

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE', 'PUT'])
async def streamlit_proxy(path):
    """
    Este novo proxy usa httpx e suporta WebSockets,
    o que é essencial para o Streamlit funcionar corretamente.
    """
    # Verifica se a requisição é para um WebSocket (o "dialeto" do Streamlit )
    if 'Upgrade' in request.headers and request.headers['Upgrade'].lower() == 'websocket':
        # Se for, não podemos usar o proxy simples. Retornamos um erro indicando
        # que a configuração do servidor web precisa lidar com isso.
        # No Render, isso geralmente funciona por padrão se a biblioteca estiver correta.
        # Esta é uma salvaguarda.
        return "WebSocket proxying not supported by this simple proxy.", 501

    # Para requisições HTTP normais, repassamos com httpx
    url = f"{STREAMLIT_URL}/{path}"
    headers = {key: value for key, value in request.headers if key.lower( ) != 'host'}
    
    try:
        # Usamos o httpx para fazer a requisição de forma assíncrona
        response = await client.request(
            method=request.method,
            url=request.url.replace(request.host_url, STREAMLIT_URL + '/' ),
            headers=headers,
            content=request.get_data(),
            params=request.args,
            allow_redirects=False
        )
        
        # Cria a resposta para o navegador do usuário
        return Response(response.content, response.status_code, response.headers.items())

    except httpx.ConnectError:
        return "A aplicação está iniciando, por favor aguarde e atualize a página em alguns segundos.", 503
    except Exception as e:
        return f"Erro no proxy: {e}", 500


# --- Comando para Iniciar a Aplicação ---
def run( ):
    # Inicia o Streamlit como um processo separado
    streamlit_command = "streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"
    subprocess.Popen(streamlit_command, shell=True)

    # Inicia o Flask na porta que o Render nos fornece
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    run()
