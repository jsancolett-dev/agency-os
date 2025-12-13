# main.py (Versão 1.0 - Orquestrador Flask + Streamlit)

import os
import uuid
import subprocess
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text

# --- Configuração Inicial e Conexão com o Banco ---

# Cria a aplicação Flask
app = Flask(__name__)

# Pega a URL do banco de dados do ambiente
db_url = os.environ.get("DATABASE_URL")

# Garante que a URL está no formato correto para SQLAlchemy
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Cria o 'engine' do SQLAlchemy para ser usado pelo webhook
engine = create_engine(db_url) if db_url else None

# --- Endpoint do Webhook ---
# Esta é a nossa "doca de carga" para a Umbler

@app.route('/webhook/umbler', methods=['POST'])
def umbler_webhook():
    # Verificação de segurança básica (opcional, mas recomendado)
    # auth_token = request.headers.get('Authorization')
    # if auth_token != "SEU_TOKEN_SECRETO_AQUI":
    #     return jsonify({"status": "error", "message": "Não autorizado"}), 401

    if not engine:
        return jsonify({"status": "error", "message": "Banco de dados não configurado"}), 500

    # Pega os dados JSON que a Umbler enviou
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Nenhum dado recebido"}), 400

    # --- LÓGICA PRINCIPAL DA AUTOMAÇÃO ---
    # Extrai as informações relevantes (os nomes dos campos podem variar!)
    # Precisaremos ajustar isso com a documentação real da Umbler
    numero_cliente = data.get('sender', {}).get('phone')
    primeira_mensagem = data.get('message', {}).get('body')
    nome_cliente = data.get('sender', {}).get('name')

    if not numero_cliente or not primeira_mensagem:
        return jsonify({"status": "error", "message": "Dados essenciais ausentes (telefone/mensagem)"}), 400

    try:
        with engine.connect() as connection:
            # 1. O cliente já existe no nosso banco? (Verifica pelo telefone)
            query_cliente = text("SELECT id FROM clientes WHERE telefone = :telefone")
            resultado = connection.execute(query_cliente, {"telefone": numero_cliente}).fetchone()
            
            cliente_id = None
            if resultado:
                # Cliente encontrado!
                cliente_id = resultado[0]
            else:
                # Cliente NÃO encontrado. Vamos criar um novo cliente "provisório".
                novo_id_cliente = uuid.uuid4()
                adscode = "WPP" + str(uuid.uuid4())[:5].upper() # Gera um AdsCode temporário
                nome_empresa = f"Lead WhatsApp ({nome_cliente or numero_cliente})"

                insert_cliente = text("""
                    INSERT INTO clientes (id, adscode, nome_empresa, nome_contato, telefone)
                    VALUES (:id, :adscode, :nome_empresa, :nome_contato, :telefone)
                """)
                connection.execute(insert_cliente, {
                    "id": novo_id_cliente,
                    "adscode": adscode,
                    "nome_empresa": nome_empresa,
                    "nome_contato": nome_cliente or "Não informado",
                    "telefone": numero_cliente
                })
                cliente_id = novo_id_cliente

            # 2. Agora que temos um cliente_id, criamos o atendimento
            insert_atendimento = text("""
                INSERT INTO atendimentos (id, cliente_id, descricao, responsavel, status)
                VALUES (:id, :cliente_id, :descricao, :responsavel, :status)
            """)
            connection.execute(insert_atendimento, {
                "id": uuid.uuid4(),
                "cliente_id": cliente_id,
                "descricao": f"Primeira mensagem: '{primeira_mensagem}'",
                "responsavel": "Não Atribuído", # Status inicial
                "status": "Aberto"
            })
            
            connection.commit()

    except Exception as e:
        # Em caso de erro, logamos e retornamos um erro 500
        print(f"ERRO NO WEBHOOK: {e}")
        return jsonify({"status": "error", "message": "Erro interno do servidor"}), 500

    # Se tudo deu certo, retornamos uma resposta de sucesso
    return jsonify({"status": "success", "message": "Atendimento criado"}), 200


# --- Comando para Iniciar a Aplicação ---
# Esta função será chamada pelo Render para iniciar tudo

def run():
    # Inicia o Streamlit como um processo separado
    # Usamos a porta 8501, que é o padrão do Streamlit
    streamlit_command = "streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"
    subprocess.Popen(streamlit_command, shell=True)

    # Inicia o Flask na porta que o Render nos fornece (geralmente 10000)
    # O Render direcionará o tráfego externo para esta porta
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    run()
