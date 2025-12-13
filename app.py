# app.py (Versão 2.0 - Módulo de Clientes)

import streamlit as st
import os
import uuid # Importa a biblioteca para gerar IDs únicos
from sqlalchemy import create_engine, text, inspect

# --- Configuração da Página ---
st.set_page_config(page_title="AgencyOS", layout="wide")
st.title("🚀 AgencyOS - Gestão de Atendimentos")
st.markdown("---")

# --- Conexão com o Banco de Dados (Já sabemos que funciona!) ---
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    st.error("ERRO CRÍTICO: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
    st.stop()

# Ajusta a URL para o dialeto do SQLAlchemy, se necessário
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)

# --- NOVA SEÇÃO: Inicialização do Banco de Dados ---
# Esta função cria a tabela 'clientes' se ela ainda não existir.
def inicializar_db():
    with engine.connect() as connection:
        inspector = inspect(engine)
        if not inspector.has_table("clientes"):
            # Usamos """ para um comando SQL de múltiplas linhas
            comando_sql = """
            CREATE TABLE clientes (
                id UUID PRIMARY KEY,
                adscode VARCHAR(10) UNIQUE NOT NULL,
                nome_empresa VARCHAR(255) NOT NULL,
                nome_contato VARCHAR(255),
                email VARCHAR(255),
                telefone VARCHAR(50),
                data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            connection.execute(text(comando_sql))
            # Confirma a transação
            connection.commit()
            st.toast("Tabela 'clientes' criada com sucesso!")

# Executa a inicialização
try:
    inicializar_db()
except Exception as e:
    st.error(f"Erro ao inicializar o banco de dados: {e}")
    st.stop()

# --- PÁGINA PRINCIPAL ---

st.header("👥 Gestão de Clientes")

# Usaremos duas colunas para organizar a interface
col1, col2 = st.columns([1, 2]) # A segunda coluna é 2x maior

# --- Coluna 1: Formulário para Adicionar Novo Cliente ---
with col1:
    st.subheader("Adicionar Novo Cliente")
    with st.form("novo_cliente_form", clear_on_submit=True):
        # Campos do formulário
        nome_empresa = st.text_input("Nome da Empresa*", placeholder="Ex: Sancolett Tech")
        nome_contato = st.text_input("Nome do Contato", placeholder="Ex: Jean Sancolett")
        email_cliente = st.text_input("E-mail do Cliente", placeholder="Ex: contato@empresa.com")
        telefone_cliente = st.text_input("Telefone/WhatsApp", placeholder="Ex: (11) 99999-8888")
        
        # Botão de submit do formulário
        submitted = st.form_submit_button("➕ Cadastrar Cliente")

        if submitted:
            if not nome_empresa:
                st.warning("O campo 'Nome da Empresa' é obrigatório.")
            else:
                try:
                    with engine.connect() as connection:
                        # Gera um ID único e um AdsCode
                        novo_id = uuid.uuid4()
                        # Pega as 3 primeiras letras da empresa e 4 dígitos aleatórios
                        adscode = nome_empresa[:3].upper() + str(uuid.uuid4())[:4]

                        # Comando SQL para inserir o novo cliente
                        comando_insert = text("""
                            INSERT INTO clientes (id, adscode, nome_empresa, nome_contato, email, telefone)
                            VALUES (:id, :adscode, :nome_empresa, :nome_contato, :email, :telefone)
                        """)
                        
                        # Executa o comando
                        connection.execute(comando_insert, {
                            "id": novo_id,
                            "adscode": adscode,
                            "nome_empresa": nome_empresa,
                            "nome_contato": nome_contato,
                            "email": email_cliente,
                            "telefone": telefone_cliente
                        })
                        connection.commit()
                        st.success(f"Cliente '{nome_empresa}' cadastrado com sucesso! AdsCode: **{adscode}**")
                        
                except Exception as e:
                    st.error(f"Ocorreu um erro ao cadastrar o cliente: {e}")


# --- Coluna 2: Lista de Clientes Cadastrados ---
with col2:
    st.subheader("Clientes Cadastrados")
    
    try:
        with engine.connect() as connection:
            # Busca todos os clientes, ordenando pelos mais recentes
            resultado = connection.execute(text("SELECT adscode, nome_empresa, nome_contato, email, telefone FROM clientes ORDER BY data_criacao DESC"))
            
            # Converte o resultado para uma lista de dicionários
            clientes = resultado.mappings().all()

            if clientes:
                # Exibe os dados em uma tabela do Streamlit
                st.dataframe(clientes, use_container_width=True)
            else:
                st.info("Nenhum cliente cadastrado ainda. Adicione um no formulário ao lado.")

    except Exception as e:
        st.error(f"Não foi possível carregar a lista de clientes: {e}")

