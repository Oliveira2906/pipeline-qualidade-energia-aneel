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

    def _dec(val: float) -> str:
        return f"{val:.2f}".replace(".", ",")

    def _pct(val: float) -> str:
        return f"{val:.1f}".replace(".", ",")

    def _mil(val: float) -> str:
        return f"{int(round(val)):,}".replace(",", ".")

    nome_top1 = str(top1_conj["nome_conjunto"]).title()
    nome_top2 = str(top2_conj["nome_conjunto"]).title()

    return (
        f"### 📋 Parecer Executivo Regulatório — Ciclo {ano_ref} (PRODIST Módulo 8)\n\n"
        f"| Dimensão Analisada | Destaque Principal | Indicador Apurado | Referência / Meta ANEEL |\n"
        f"| :--- | :--- | :--- | :--- |\n"
        f"| **Maior Pressão Regulatória** | **{pior_dist['sigla_agente']} ({pior_dist['uf']})** | DEC: **{_dec(pior_dist['dec_apurado_ponderado'])} h** ({_dec(pior_dist['indice_severidade_dec'])}x) | Limite: **{_dec(pior_dist['dec_limite_ponderado'])} h** |\n"
        f"| **Benchmark de Confiabilidade** | **{melhor_dist['sigla_agente']} ({melhor_dist['uf']})** | Severidade: **{_dec(melhor_dist['indice_severidade_dec'])}x** | Limite: **{_dec(melhor_dist['dec_limite_ponderado'])} h** |\n"
        f"| **Conjunto Mais Crítico (#1)** | **{nome_top1} ({top1_conj['sigla_agente']})** | **{_mil(top1_conj['uc_horas_excedentes'])}** UC-h excedentes | DEC: {_dec(top1_conj['dec_apurado'])} h vs. {_dec(top1_conj['dec_limite'])} h |\n"
        f"| **Perfil Físico Mais Exposto** | **{perfil_critico['perfil_fisico_conjunto']}** | Transgressão: **{_pct(perfil_critico['taxa_transgressao_dec_pct'])}%** | DEC Médio: {_dec(perfil_critico['dec_medio_apurado'])} h |\n\n"
        f"---\n\n"
        f"#### 📌 1. Conformidade por Distribuidora (Pergunta 1)\n"
        f"* **Concessionária Crítica:** A **{pior_dist['sigla_agente']} ({pior_dist['uf']})** lidera o ranking de severidade em {ano_ref}, "
        f"com DEC médio ponderado de **{_dec(pior_dist['dec_apurado_ponderado'])} h** frente ao teto regulatório de **{_dec(pior_dist['dec_limite_ponderado'])} h** "
        f"(Índice de Severidade de **{_dec(pior_dist['indice_severidade_dec'])}x** e **{_pct(pior_dist['pct_conjuntos_transgressores_dec'])}%** dos conjuntos em transgressão).\n"
        f"* **Referência Positiva:** Na outra extremidade, a **{melhor_dist['sigla_agente']} ({melhor_dist['uf']})** manteve operação dentro dos parâmetros da ANEEL, "
        f"com índice de severidade de **{_dec(melhor_dist['indice_severidade_dec'])}x**.\n\n"
        f"#### 🚨 2. Conjuntos Críticos e Impacto ao Consumidor (Pergunta 2)\n"
        f"* **1º Lugar em Impacto:** O conjunto **{nome_top1} ({top1_conj['sigla_agente']})** gerou **{_mil(top1_conj['uc_horas_excedentes'])} consumidor-horas perdidas acima da meta** "
        f"(DEC apurado de **{_dec(top1_conj['dec_apurado'])} h** contra limite de **{_dec(top1_conj['dec_limite'])} h**).\n"
        f"* **2º Lugar em Impacto:** O conjunto **{nome_top2} ({top2_conj['sigla_agente']})** acumulou **{_mil(top2_conj['uc_horas_excedentes'])} consumidor-horas excedentes**, "
        f"evidenciando alta concentração de risco regulatório em grandes centros urbanos.\n\n"
        f"#### 🌐 3. Perfil Físico-Elétrico × Qualidade da Rede (Pergunta 3)\n"
        f"* Conjuntos de perfil **{perfil_critico['perfil_fisico_conjunto']}** registraram DEC médio de **{_dec(perfil_critico['dec_medio_apurado'])} h** "
        f"(meta média de **{_dec(perfil_critico['dec_medio_limite'])} h**) e taxa de violação de **{_pct(perfil_critico['taxa_transgressao_dec_pct'])}%**.\n"
        f"* Enquanto redes rurais extensas elevam o **DEC absoluto** pelo tempo de deslocamento das equipes de campo, "
        f"as transgressões em conjuntos metropolitanos multiplicam o volume de **Consumidor × Horas**, elevando as compensações financeiras (DIC/FIC).\n\n"
        f"> **💡 Recomendação de Engenharia e Regulação:** Priorizar a instalação de religadores automáticos telecomandados (*Self-Healing*) "
        f"e cronograma intensivo de poda preventiva pré-verão nos conjuntos metropolitanos transgressores da **{pior_dist['sigla_agente']}**, "
        f"mitigando o produto `Desvio DEC × UCs` e a exposição a penalidades da fiscalização ANEEL."
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
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    with duckdb.connect(str(DEFAULT_DB_PATH)) as conn:
        resumo = generate_ai_executive_summary(conn)
        print(resumo)
