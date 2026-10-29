"""Dashboard Regulatório ANEEL (Seção 07) — Consumo exclusivo da camada MARTS.

Regra de Arquitetura:
- Este painel lê APENAS tabelas do schema `marts` no DuckDB.
- Nenhum cálculo de regra de negócio, agregação ou transformação é feito na tela.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aneel_continuidade.duckdb"

st.set_page_config(
    page_title="Monitor Regulatório ANEEL — DEC & FEC",
    page_icon="⚡",
    layout="wide",
)


def query_marts(sql: str, params: list | None = None) -> pd.DataFrame:
    """Executa consulta somente-leitura exclusivamente sobre a camada `marts`."""
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        if params:
            return con.execute(sql, params).df()
        return con.execute(sql).df()


def main() -> None:
    st.title("⚡ Monitor Regulatório de Continuidade da Distribuição (ANEEL — DEC & FEC)")
    st.caption(
        "Painel Analítico (Seção 07) — Dados lidos exclusivamente da camada `marts` no DuckDB (zero cálculo na tela)."
    )

    if not DB_PATH.exists():
        st.error(
            f"Banco de dados não encontrado em `{DB_PATH}`. Execute `python -m src.run_pipeline` antes de abrir o painel."
        )
        st.stop()

    # Filtros laterais alimentados pela camada marts
    anos_df = query_marts("SELECT DISTINCT ano FROM marts.mart_kpis_globais ORDER BY ano DESC")
    distribuidoras_df = query_marts(
        "SELECT DISTINCT filtro_distribuidora FROM marts.mart_kpis_globais ORDER BY filtro_distribuidora"
    )

    st.sidebar.header("Filtros de Consulta (Marts)")
    ano_selecionado = st.sidebar.selectbox("Ano de Apuração", anos_df["ano"].tolist(), index=0)
    opcoes_dist = ["TODAS"] + [
        d for d in distribuidoras_df["filtro_distribuidora"].tolist() if d != "TODAS"
    ]
    dist_selecionada = st.sidebar.selectbox("Distribuidora (Agente ANEEL)", opcoes_dist, index=0)

    # 1. Cartões de Indicadores (lidos prontos de marts.mart_kpis_globais)
    kpi_row = query_marts(
        """
        SELECT *
        FROM marts.mart_kpis_globais
        WHERE ano = ? AND filtro_distribuidora = ?
        """,
        [int(ano_selecionado), dist_selecionada],
    ).iloc[0]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(
        "Unidades Consumidoras Atendidas",
        f"{int(kpi_row['total_uc_atendidas']):,}".replace(",", "."),
        f"{int(kpi_row['total_conjuntos'])} conjuntos elétricos",
    )
    col2.metric(
        "DEC Apurado Ponderado (h)",
        f"{kpi_row['dec_apurado_ponderado']:.2f} h",
        f"{kpi_row['desvio_dec_ponderado_horas']:+.2f} h vs Limite ({kpi_row['dec_limite_ponderado']:.2f} h)",
        delta_color="inverse",
    )
    col3.metric(
        "FEC Apurado Ponderado (int.)",
        f"{kpi_row['fec_apurado_ponderado']:.2f}",
        f"Limite: {kpi_row['fec_limite_ponderado']:.2f}",
    )
    col4.metric(
        "% Conjuntos Transgressores DEC",
        f"{kpi_row['pct_conjuntos_transgressores_dec']:.1f}%",
        f"{int(kpi_row['qtd_conjuntos_transgressores_dec'])} de {int(kpi_row['total_conjuntos'])} conjuntos",
        delta_color="inverse",
    )
    col5.metric(
        "Consumidor × Horas Excedentes",
        f"{int(kpi_row['total_uc_horas_excedentes']):,}".replace(",", "."),
        "Horas acima do limite ANEEL",
        delta_color="inverse",
    )

    st.divider()

    # 2. Parecer Executivo IA (lido diretamente de marts.mart_parecer_executivo_ia)
    df_parecer = query_marts("SELECT * FROM marts.mart_parecer_executivo_ia LIMIT 1")
    if not df_parecer.empty:
        with st.expander("🤖 Parecer Executivo Regulatório (Camada Marts + IA)", expanded=True):
            st.markdown(df_parecer.iloc[0]["parecer_markdown"])
            st.caption(
                f"Gerado por: `{df_parecer.iloc[0]['modelo_gerador']}` em `{df_parecer.iloc[0]['gerado_em']}`"
            )

    # 3. Pergunta 1 e Pergunta 2: Conformidade das Distribuidoras e Ranking de Conjuntos Críticos
    c_left, c_right = st.columns(2)

    with c_left:
        st.subheader("1. Conformidade Regulatória por Distribuidora")
        df_perf = query_marts(
            """
            SELECT
                sigla_agente,
                uf,
                dec_apurado_ponderado,
                dec_limite_ponderado,
                indice_severidade_dec,
                pct_conjuntos_transgressores_dec,
                situacao_global_distribuidora
            FROM marts.mart_performance_distribuidoras
            WHERE ano = ?
            ORDER BY indice_severidade_dec DESC
            """,
            [int(ano_selecionado)],
        )
        fig_dist = px.bar(
            df_perf,
            x="sigla_agente",
            y=["dec_apurado_ponderado", "dec_limite_ponderado"],
            barmode="group",
            title=f"DEC Apurado Ponderado vs. Limite Regulatório ANEEL ({ano_selecionado})",
            labels={"value": "Horas Anuais (DEC)", "sigla_agente": "Distribuidora", "variable": "Indicador"},
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with c_right:
        st.subheader("2. Top Conjuntos Críticos (Consumidor × Horas Excedentes)")
        if dist_selecionada == "TODAS":
            df_conj = query_marts(
                """
                SELECT
                    ranking_criticidade_ano,
                    nome_conjunto,
                    sigla_agente,
                    uf,
                    perfil_fisico_conjunto,
                    dec_apurado,
                    dec_limite,
                    desvio_dec_horas,
                    uc_horas_excedentes,
                    status_regulatorio
                FROM marts.mart_ranking_conjuntos_criticos
                WHERE ano = ?
                ORDER BY ranking_criticidade_ano ASC
                LIMIT 10
                """,
                [int(ano_selecionado)],
            )
        else:
            df_conj = query_marts(
                """
                SELECT
                    ranking_criticidade_ano,
                    nome_conjunto,
                    sigla_agente,
                    uf,
                    perfil_fisico_conjunto,
                    dec_apurado,
                    dec_limite,
                    desvio_dec_horas,
                    uc_horas_excedentes,
                    status_regulatorio
                FROM marts.mart_ranking_conjuntos_criticos
                WHERE ano = ? AND sigla_agente = ?
                ORDER BY ranking_criticidade_ano ASC
                """,
                [int(ano_selecionado), dist_selecionada],
            )

        fig_conj = px.bar(
            df_conj,
            x="uc_horas_excedentes",
            y="nome_conjunto",
            color="sigla_agente",
            orientation="h",
            title=f"Conjuntos com Maior Volume de Consumidor × Horas Excedentes ({ano_selecionado})",
            labels={
                "uc_horas_excedentes": "Consumidor × Horas Acima da Meta",
                "nome_conjunto": "Conjunto Elétrico",
                "sigla_agente": "Distribuidora",
            },
        )
        fig_conj.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_conj, use_container_width=True)

    # 4. Pergunta 3 e Pergunta 4: Perfil Físico-Elétrico e Evolução Mensal/Sazonal
    c_bot_left, c_bot_right = st.columns(2)

    with c_bot_left:
        st.subheader("3. Perfil Físico-Elétrico × Qualidade da Rede")
        df_perfil = query_marts(
            """
            SELECT
                perfil_fisico_conjunto,
                qtd_conjuntos,
                densidade_media_uc_km2,
                extensao_media_rede_km,
                dec_medio_apurado,
                dec_medio_limite,
                taxa_transgressao_dec_pct,
                taxa_transgressao_fec_pct
            FROM marts.mart_perfil_fisico_qualidade
            WHERE ano = ?
            ORDER BY dec_medio_apurado DESC
            """,
            [int(ano_selecionado)],
        )
        fig_perfil = px.bar(
            df_perfil,
            x="perfil_fisico_conjunto",
            y=["dec_medio_apurado", "dec_medio_limite"],
            barmode="group",
            title="DEC Médio Apurado vs. Limite por Perfil Físico-Elétrico do Conjunto",
            labels={"value": "Horas (DEC)", "perfil_fisico_conjunto": "Perfil Físico do Conjunto"},
        )
        st.plotly_chart(fig_perfil, use_container_width=True)

    with c_bot_right:
        st.subheader("4. Sazonalidade Mensal e Impacto do Período Chuvoso")
        if dist_selecionada == "TODAS":
            df_evol = query_marts(
                """
                SELECT
                    nome_mes,
                    sigla_agente,
                    dec_mensal_ponderado,
                    referencia_mensal_limite_dec,
                    estacao_operacional
                FROM marts.mart_evolucao_continuidade
                WHERE ano = ?
                ORDER BY mes, sigla_agente
                """,
                [int(ano_selecionado)],
            )
        else:
            df_evol = query_marts(
                """
                SELECT
                    nome_mes,
                    sigla_agente,
                    dec_mensal_ponderado,
                    referencia_mensal_limite_dec,
                    estacao_operacional
                FROM marts.mart_evolucao_continuidade
                WHERE ano = ? AND sigla_agente = ?
                ORDER BY mes
                """,
                [int(ano_selecionado), dist_selecionada],
            )
        fig_evol = px.line(
            df_evol,
            x="nome_mes",
            y="dec_mensal_ponderado",
            color="sigla_agente",
            markers=True,
            title=f"Curva Sazonal do DEC Mensal Ponderado ({ano_selecionado})",
            labels={
                "nome_mes": "Mês de Apuração",
                "dec_mensal_ponderado": "DEC Mensal (h)",
                "sigla_agente": "Distribuidora",
            },
        )
        st.plotly_chart(fig_evol, use_container_width=True)

    st.subheader("Tabela Detalhada da Camada `marts.mart_ranking_conjuntos_criticos`")
    st.dataframe(df_conj, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
