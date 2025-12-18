# app.py (Versão 4.0 Restaurada - Apenas Streamlit)

import streamlit as st
import os
import uuid
from sqlalchemy import create_engine, text, inspect
import pandas as pd
import plotly.express as px

# --- Configuração da Página e Constantes ---
st.set_page_config(page_title="AgencyOS", layout="wide")

MEMBROS_EQUIPE = ["Jean", "Membro 2", "Membro 3", "Membro 4"]

# --- Conexão com o Banco de Dados ---
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    st.error("ERRO CRÍTICO: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
    st.stop()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
try:
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"Erro ao criar a conexão com o banco de dados: {e}")
    st.stop()

# --- Inicialização do Banco de Dados ---
def inicializar_db():
    with engine.connect() as connection:
        inspector = inspect(engine)
        if not inspector.has_table("clientes"):
            comando_sql_clientes = "CREATE TABLE clientes (id UUID PRIMARY KEY, adscode VARCHAR(10) UNIQUE NOT NULL, nome_empresa VARCHAR(255) NOT NULL, nome_contato VARCHAR(255), email VARCHAR(255), telefone VARCHAR(50), data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
            connection.execute(text(comando_sql_clientes))
            connection.commit()
        if not inspector.has_table("atendimentos"):
            comando_sql_atendimentos = "CREATE TABLE atendimentos (id UUID PRIMARY KEY, cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE, descricao TEXT NOT NULL, responsavel VARCHAR(100) NOT NULL, status VARCHAR(50) NOT NULL, csat INT, data_atendimento TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
            connection.execute(text(comando_sql_atendimentos))
            connection.commit()
try:
    inicializar_db()
except Exception as e:
    st.error(f"Erro ao inicializar o banco de dados: {e}")
    st.stop()

# --- Funções de Apoio ---
def carregar_clientes():
    try:
        with engine.connect() as connection:
            query = "SELECT id, nome_empresa, adscode FROM clientes ORDER BY nome_empresa ASC"
            df_clientes = pd.read_sql(query, connection)
            df_clientes['display_name'] = df_clientes['nome_empresa'] + " (" + df_clientes['adscode'] + ")"
            return df_clientes
    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")
        return pd.DataFrame(columns=['id', 'display_name'])

# --- Interface Principal com Abas ---
st.title("🚀 AgencyOS - Gestão de Atendimentos")
tab_dash, tab_atend, tab_cli = st.tabs(["📊 Dashboards", "📈 Atendimentos", "👥 Clientes"])

# --- Aba Dashboards ---
with tab_dash:
    st.header("Painel de Controle e Métricas")
    try:
        with engine.connect() as connection:
            query_all_data = "SELECT responsavel, status, csat FROM atendimentos"
            df_data = pd.read_sql(query_all_data, connection)
        if df_data.empty:
            st.info("Ainda não há dados de atendimentos suficientes para gerar os dashboards.")
        else:
            st.subheader("Visão Geral")
            kpi1, kpi2, kpi3 = st.columns(3)
            total_atendimentos = len(df_data)
            kpi1.metric(label="Total de Atendimentos Registrados", value=total_atendimentos)
            media_csat = df_data['csat'].dropna().mean()
            kpi2.metric(label="Média Geral de CSAT", value=f"{media_csat:.2f} ⭐" if media_csat > 0 else "N/A")
            atendimentos_concluidos = len(df_data[df_data['status'] == 'Concluído'])
            kpi3.metric(label="Atendimentos Concluídos", value=atendimentos_concluidos)
            st.markdown("---")
            col_graph1, col_graph2 = st.columns(2)
            with col_graph1:
                st.subheader("Produtividade por Equipe")
                produtividade = df_data['responsavel'].value_counts().reset_index()
                produtividade.columns = ['Responsável', 'Número de Atendimentos']
                fig_prod = px.bar(produtividade, x='Responsável', y='Número de Atendimentos', title="Total de Atendimentos por Membro da Equipe", text_auto=True)
                st.plotly_chart(fig_prod, use_container_width=True)
            with col_graph2:
                st.subheader("Qualidade do Atendimento (CSAT)")
                csat_por_responsavel = df_data.dropna(subset=['csat']).groupby('responsavel')['csat'].mean().reset_index()
                csat_por_responsavel.columns = ['Responsável', 'Média de CSAT']
                fig_csat = px.bar(csat_por_responsavel, x='Responsável', y='Média de CSAT', title="Média de CSAT por Membro da Equipe", text_auto='.2f')
                fig_csat.update_yaxes(range=[0, 5.5])
                st.plotly_chart(fig_csat, use_container_width=True)
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar os dashboards: {e}")

# --- Aba Atendimentos ---
with tab_atend:
    st.header("Gestão de Atendimentos (OS)")
    df_clientes = carregar_clientes()
    col_form, col_lista = st.columns([1, 2])
    with col_form:
        st.subheader("Registrar Novo Atendimento")
        if not df_clientes.empty:
            with st.form("novo_atendimento_form", clear_on_submit=True):
                cliente_display_name = st.selectbox("Cliente*", options=df_clientes['display_name'], index=None, placeholder="Selecione o cliente")
                responsavel = st.selectbox("Responsável*", options=MEMBROS_EQUIPE, index=None, placeholder="Selecione o responsável")
                descricao = st.text_area("Descrição do Serviço*", placeholder="Descreva o serviço realizado...")
                status = st.selectbox("Status*", ["Aberto", "Em Andamento", "Concluído", "Aguardando Cliente"])
                csat = st.selectbox("Nota CSAT (1 a 5)", [None, 1, 2, 3, 4, 5], index=0, help="Deixe em branco se ainda não houver nota.")
                submitted = st.form_submit_button("➕ Registrar Atendimento")
                if submitted:
                    if not all([cliente_display_name, responsavel, descricao, status]):
                        st.warning("Por favor, preencha todos os campos obrigatórios (*).")
                    else:
                        try:
                            cliente_id = df_clientes[df_clientes['display_name'] == cliente_display_name]['id'].iloc[0]
                            with engine.connect() as connection:
                                comando_insert = text("INSERT INTO atendimentos (id, cliente_id, descricao, responsavel, status, csat) VALUES (:id, :cliente_id, :descricao, :responsavel, :status, :csat)")
                                connection.execute(comando_insert, {"id": uuid.uuid4(), "cliente_id": cliente_id, "descricao": descricao, "responsavel": responsavel, "status": status, "csat": csat})
                                connection.commit()
                                st.success("Atendimento registrado com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao registrar atendimento: {e}")
        else:
            st.warning("Cadastre um cliente na aba 'Clientes' antes de registrar um atendimento.")
    with col_lista:
        st.subheader("Últimos Atendimentos Registrados")
        try:
            with engine.connect() as connection:
                query_atendimentos = "SELECT a.data_atendimento, c.nome_empresa, a.responsavel, a.descricao, a.status, a.csat FROM atendimentos a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.data_atendimento DESC LIMIT 50;"
                df_atendimentos = pd.read_sql(query_atendimentos, connection)
                df_atendimentos.rename(columns={'data_atendimento': 'Data', 'nome_empresa': 'Cliente', 'responsavel': 'Responsável', 'descricao': 'Descrição', 'status': 'Status', 'csat': 'CSAT'}, inplace=True)
                if not df_atendimentos.empty:
                    st.dataframe(df_atendimentos, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum atendimento registrado ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar atendimentos: {e}")

# --- Aba Clientes ---
with tab_cli:
    st.header("Gestão de Clientes")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Adicionar Novo Cliente")
        with st.form("novo_cliente_form", clear_on_submit=True):
            nome_empresa = st.text_input("Nome da Empresa*", placeholder="Ex: Sancolett Tech")
            nome_contato = st.text_input("Nome do Contato", placeholder="Ex: Jean Sancolett")
            email_cliente = st.text_input("E-mail do Cliente", placeholder="Ex: contato@empresa.com")
            telefone_cliente = st.text_input("Telefone/WhatsApp", placeholder="Ex: (11) 99999-8888")
            submitted = st.form_submit_button("➕ Cadastrar Cliente")
            if submitted:
                if not nome_empresa:
                    st.warning("O campo 'Nome da Empresa' é obrigatório.")
                else:
                    try:
                        with engine.connect() as connection:
                            novo_id = uuid.uuid4()
                            adscode = nome_empresa[:3].upper() + str(uuid.uuid4())[:4].upper()
                            comando_insert = text("INSERT INTO clientes (id, adscode, nome_empresa, nome_contato, email, telefone) VALUES (:id, :adscode, :nome_empresa, :nome_contato, :email, :telefone)")
                            connection.execute(comando_insert, {"id": novo_id, "adscode": adscode, "nome_empresa": nome_empresa, "nome_contato": nome_contato, "email": email_cliente, "telefone": telefone_cliente})
                            connection.commit()
                            st.success(f"Cliente '{nome_empresa}' cadastrado com sucesso! AdsCode: **{adscode}**")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao cadastrar o cliente: {e}")
    with col2:
        st.subheader("Clientes Cadastrados")
        try:
            df_todos_clientes = carregar_clientes()
            if not df_todos_clientes.empty:
                st.dataframe(df_todos_clientes[['adscode', 'nome_empresa']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum cliente cadastrado ainda.")
        except Exception as e:
            st.error(f"Não foi possível carregar a lista de clientes: {e}")
