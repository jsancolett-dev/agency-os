# app.py
import streamlit as st
import os
from sqlalchemy import create_engine, text

# --- Configuração da Página ---
st.set_page_config(page_title="AgencyOS", layout="centered")
st.title("🚀 AgencyOS - Teste de Conexão")

# --- Conexão com o Banco de Dados ---
# Pega a string de conexão da variável de ambiente do Render
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    st.error("ERRO: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
    st.info("Por favor, configure esta variável no ambiente do seu serviço no Render.")
    st.stop() # Para a execução se não houver URL

try:
    # Tenta criar uma "engine" de conexão com o banco de dados
    engine = create_engine(db_url)

    # Tenta estabelecer uma conexão real e executar um comando simples
    with engine.connect() as connection:
        # O comando 'SELECT 1' é um "ping" universal para bancos de dados
        result = connection.execute(text("SELECT 1"))
        
        # Se chegamos até aqui, a conexão foi um sucesso!
        st.success("🎉 CONEXÃO COM O BANCO DE DADOS BEM-SUCEDIDA! 🎉")
        st.balloons()
        st.info(f"Conectado com sucesso ao banco de dados.")
        st.caption("Agora estamos prontos para construir o resto da aplicação.")

except Exception as e:
    # Se qualquer coisa der errado, mostra uma mensagem de erro detalhada
    st.error("❌ FALHA NA CONEXÃO COM O BANCO DE DADOS ❌")
    st.write("Ocorreu um erro ao tentar conectar ao PostgreSQL:")
    st.error(e)

