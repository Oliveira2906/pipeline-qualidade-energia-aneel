"""Módulo de Inteligência Artificial para geração de Parecer Regulatório Executivo.

Lê exclusivamente os indicadores consolidados na camada `marts` e sintetiza diagnósticos
regulatórios sobre conformidade de DEC/FEC, conjuntos críticos e perfil físico-elétrico.
Utiliza a SDK `google-genai` (`gemini-3.8-flash`) via Interactions API quando `GEMINI_API_KEY`
está configurada, com síntese analítica estruturada determinística e persistência em
`marts.mart_parecer_executivo_ia` para leitura direta pelo Dashboard.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from google import genai

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/aneel_continuidade.duckdb")


def _build_deterministic_synthesis(con: duckdb.DuckDBPyConnection, ano_ref: int = 2024) -> str:
    """Constrói parecer analítico baseado nos indicadores da camada `marts`."""
    df_dist = con.execute(
        f"""
        SELECT
            sigla_agente,
            uf,
            dec_apurado_ponderado,
            dec_limite_ponderado,
            indice_severidade_dec,
            pct_conjuntos_transgressores_dec,
            total_uc_horas_excedentes
        FROM marts.mart_performance_distribuidoras
        WHERE ano = {ano_ref}
        ORDER BY indice_severidade_dec DESC
        """
    ).df()

    df_top_conj = con.execute(
        f"""
        SELECT
            nome_conjunto,
            sigla_agente,
            uf,
            perfil_fisico_conjunto,
            dec_apurado,
            dec_limite,
            desvio_dec_horas,
            uc_horas_excedentes
        FROM marts.mart_ranking_conjuntos_criticos
        WHERE ano = {ano_ref}
        ORDER BY ranking_criticidade_ano ASC
        LIMIT 3
        """
    ).df()

    df_perfil = con.execute(
        f"""
        SELECT
            perfil_fisico_conjunto,
            dec_medio_apurado,
            dec_medio_limite,
            taxa_transgressao_dec_pct
        FROM marts.mart_perfil_fisico_qualidade
        WHERE ano = {ano_ref}
        ORDER BY severidade_media_dec DESC
        """
    ).df()

    pior_dist = df_dist.iloc[0]
    melhor_dist = df_dist.iloc[-1]
    top1_conj = df_top_conj.iloc[0]
    top2_conj = df_top_conj.iloc[1]
    perfil_critico = df_perfil.iloc[0]

    return (
        f"### Parecer Executivo Regulatório — Ciclo {ano_ref} (ANEEL DEC & FEC)\n\n"
        f"1. **Conformidade por Distribuidora (Pergunta 1):** A concessionária com maior pressão regulatória em {ano_ref} é a "
        f"**{pior_dist['sigla_agente']} ({pior_dist['uf']})**, registrando DEC médio ponderado de **{pior_dist['dec_apurado_ponderado']:.2f}h** "
        f"contra o limite de **{pior_dist['dec_limite_ponderado']:.2f}h** (Índice de Severidade = **{pior_dist['indice_severidade_dec']:.2f}x** "
        f"e **{pior_dist['pct_conjuntos_transgressores_dec']:.1f}%** dos conjuntos em transgressão). Na ponta oposta de alta confiabilidade, "
        f"**{melhor_dist['sigla_agente']} ({melhor_dist['uf']})** operou com índice de severidade de **{melhor_dist['indice_severidade_dec']:.2f}x**.\n"
        f"2. **Conjuntos Críticos e Impacto ao Consumidor (Pergunta 2):** O conjunto **#{1} {top1_conj['nome_conjunto']} ({top1_conj['sigla_agente']})** "
        f"lidera o impacto ao consumidor com **{top1_conj['uc_horas_excedentes']:,.0f} consumidor-horas perdidas acima da meta** "
        f"(DEC apurado de {top1_conj['dec_apurado']:.2f}h vs limite de {top1_conj['dec_limite']:.2f}h), seguido por "
        f"**{top2_conj['nome_conjunto']} ({top2_conj['sigla_agente']})** com **{top2_conj['uc_horas_excedentes']:,.0f} UC-horas excedentes**.\n"
        f"3. **Perfil Físico-Elétrico × Qualidade da Rede (Pergunta 3):** Conjuntos classificados como **{perfil_critico['perfil_fisico_conjunto']}** "
        f"apresentaram DEC médio de **{perfil_critico['dec_medio_apurado']:.2f}h** (meta média de {perfil_critico['dec_medio_limite']:.2f}h) "
        f"e taxa de transgressão de **{perfil_critico['taxa_transgressao_dec_pct']:.1f}%**, confirmando o peso da extensão de alimentadores "
        f"e do tempo de deslocamento de equipes em redes rurais/extensas e o alto impacto populacional nas transgressões metropolitanas.\n"
        f"4. **Recomendação de Engenharia e Regulação:** Priorizar religadores automáticos telecomandados (Self-Healing) e poda preventiva "
        f"pré-verão nos conjuntos metropolitanos transgressores da **{pior_dist['sigla_agente']}**, onde o produto `Desvio DEC × UCs` "
        f"maximiza o risco de compensações financeiras (DIC/FIC) e sanções da fiscalização ANEEL."
    )


def generate_ai_executive_summary(
    con: duckdb.DuckDBPyConnection,
    ano_ref: int = 2024,
) -> str:
    """Gera parecer executivo com IA (`gemini-3.8-flash`) a partir da camada `marts` e grava em `marts.mart_parecer_executivo_ia`."""
    base_synthesis = _build_deterministic_synthesis(con, ano_ref=ano_ref)
    final_text = base_synthesis
    modelo_utilizado = "Síntese Analítica Estruturada (Marts Layer)"

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            interaction = client.interactions.create(
                model="gemini-3.8-flash",
                system_instruction=(
                    "Você é um Especialista em Regulação do Setor Elétrico Brasileiro (ANEEL - PRODIST Módulo 8). "
                    "Sintetize em português executivo e objetivo os indicadores de DEC e FEC da camada marts abaixo."
                ),
                input=f"Baseado nos indicadores consolidados da camada marts:\n\n{base_synthesis}\n\n"
                "Elabore um parecer executivo conciso em 4 tópicos mantendo os números exatos.",
            )
            if interaction.output_text:
                final_text = interaction.output_text
                modelo_utilizado = "gemini-3.8-flash (Interactions API)"
                logger.info("Parecer executivo gerado via Gemini API (gemini-3.8-flash).")
        except Exception as exc:
            logger.warning("Gemini API não utilizada (%s). Mantendo síntese analítica estruturada.", exc)

    con.execute("CREATE SCHEMA IF NOT EXISTS marts;")
    con.execute(
        """
        CREATE OR REPLACE TABLE marts.mart_parecer_executivo_ia (
            ano_referencia INTEGER,
            modelo_gerador VARCHAR,
            gerado_em VARCHAR,
            parecer_markdown VARCHAR
        );
        """
    )
    con.execute(
        "INSERT INTO marts.mart_parecer_executivo_ia VALUES (?, ?, ?, ?);",
        [ano_ref, modelo_utilizado, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), final_text],
    )
    return final_text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    with duckdb.connect(str(DEFAULT_DB_PATH)) as conn:
        resumo = generate_ai_executive_summary(conn)
        print(resumo)
