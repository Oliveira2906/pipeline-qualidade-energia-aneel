"""Testes unitários isolados para o pipeline de continuidade da ANEEL (DEC e FEC).

Regra estrita do projeto (Passo 4.6):
- Todos os testes rodam exclusivamente em memória (`duckdb.connect(":memory:")`).
- Utilizam dados sintéticos ("inventados") criados via fixtures do pytest.
- NENHUM teste abre ou depende do arquivo de banco de dados real do projeto (`data/*.duckdb`).
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from src.build_marts import build_marts_layer
from src.extract_raw import load_raw_layer
from src.transform_refined import transform_refined_layer


@pytest.fixture()
def synthetic_raw_tables() -> dict[str, pd.DataFrame]:
    """Cria dados brutos inventados simulando problemas reais da origem ANEEL:
    - números como texto com vírgula decimal ('12,50')
    - espaços laterais nos nomes e siglas (' DISTRIBUIDORA ALFA ')
    - linhas duplicadas de reenvio com datas diferentes
    - valores negativos inválidos que devem ser filtrados na camada refined
    """
    atributos = pd.DataFrame(
        [
            # Conjunto Urbano denso (duplicado com atualização posterior)
            {
                "DatGeracaoConjuntoDados": "2025-01-10",
                "SigAgente": " DIST ALFA ",
                "NumCNPJ": "11.111.111/0001-11",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": " centro metropolitano ",
                "SigUF": "sp",
                "AnoIndice": "2024",
                "QtdUCAtendidas": "95000",
                "VlrAreaConjuntoKm2": "25,00",
                "VlrExtensaoRedeKm": "500,00",
                "QtdSubestacoes": "3",
            },
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11.111.111/0001-11",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigUF": "SP",
                "AnoIndice": "2024",
                "QtdUCAtendidas": "100000",
                "VlrAreaConjuntoKm2": "25,00",
                "VlrExtensaoRedeKm": "500,00",
                "QtdSubestacoes": "3",
            },
            # Conjunto Rural extenso
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST BETA",
                "NumCNPJ": "22222222000122",
                "IdeConjUndConsumidoras": "9002",
                "DscConjUndConsumidoras": "SERTAO RURAL",
                "SigUF": "MG",
                "AnoIndice": "2024",
                "QtdUCAtendidas": "20000",
                "VlrAreaConjuntoKm2": "1000,00",
                "VlrExtensaoRedeKm": "2000,00",
                "QtdSubestacoes": "1",
            },
            # Registro inválido (UCs zeradas) que deve ser descartado na refined
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST INVALIDA",
                "NumCNPJ": "99999999000199",
                "IdeConjUndConsumidoras": "9999",
                "DscConjUndConsumidoras": "CONJUNTO FANTASMA",
                "SigUF": "RJ",
                "AnoIndice": "2024",
                "QtdUCAtendidas": "0",
                "VlrAreaConjuntoKm2": "10,00",
                "VlrExtensaoRedeKm": "50,00",
                "QtdSubestacoes": "0",
            },
        ]
    )

    limites = pd.DataFrame(
        [
            # Conjunto 9001: Limite DEC = 8,00 | Limite FEC = 5,00
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "DEC",
                "AnoLimite": "2024",
                "VlrLimiteEnviado": "8,00",
            },
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "FEC",
                "AnoLimite": "2024",
                "VlrLimiteEnviado": "5,00",
            },
            # Conjunto 9002: Limite DEC = 15,00 | Limite FEC = 10,00
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST BETA",
                "NumCNPJ": "22222222000122",
                "IdeConjUndConsumidoras": "9002",
                "DscConjUndConsumidoras": "SERTAO RURAL",
                "SigIndicador": "DEC",
                "AnoLimite": "2024",
                "VlrLimiteEnviado": "15,00",
            },
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST BETA",
                "NumCNPJ": "22222222000122",
                "IdeConjUndConsumidoras": "9002",
                "DscConjUndConsumidoras": "SERTAO RURAL",
                "SigIndicador": "FEC",
                "AnoLimite": "2024",
                "VlrLimiteEnviado": "10,00",
            },
        ]
    )

    indicadores = pd.DataFrame(
        [
            # Conjunto 9001 Anual (periodo 13): DEC apurado = 10,50 (ESTOURO de +2,50h) | FEC = 4,00 (CONFORME)
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "DEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "13",
                "VlrIndiceEnviado": "10,50",
            },
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "FEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "13",
                "VlrIndiceEnviado": "4,00",
            },
            # Conjunto 9002 Anual (periodo 13): DEC = 12,00 (CONFORME) | FEC = 8,50 (CONFORME)
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST BETA",
                "NumCNPJ": "22222222000122",
                "IdeConjUndConsumidoras": "9002",
                "DscConjUndConsumidoras": "SERTAO RURAL",
                "SigIndicador": "DEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "13",
                "VlrIndiceEnviado": "12,00",
            },
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST BETA",
                "NumCNPJ": "22222222000122",
                "IdeConjUndConsumidoras": "9002",
                "DscConjUndConsumidoras": "SERTAO RURAL",
                "SigIndicador": "FEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "13",
                "VlrIndiceEnviado": "8,50",
            },
            # Registro Mensal (Janeiro = 01) para testar mart_evolucao_continuidade
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "DEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "01",
                "VlrIndiceEnviado": "1,80",
            },
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "FEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "01",
                "VlrIndiceEnviado": "0,75",
            },
            # Registro inválido com valor negativo (deve ser ignorado na refined)
            {
                "DatGeracaoConjuntoDados": "2025-02-01",
                "SigAgente": "DIST ALFA",
                "NumCNPJ": "11111111000111",
                "IdeConjUndConsumidoras": "9001",
                "DscConjUndConsumidoras": "CENTRO METROPOLITANO",
                "SigIndicador": "DEC",
                "AnoIndice": "2024",
                "NumPeriodoIndice": "02",
                "VlrIndiceEnviado": "-5,00",
            },
        ]
    )

    return {
        "atributos_conjuntos": atributos,
        "limites_continuidade": limites,
        "indicadores_continuidade": indicadores,
    }


@pytest.fixture()
def in_memory_pipeline_db(synthetic_raw_tables: dict[str, pd.DataFrame]) -> duckdb.DuckDBPyConnection:
    """Executa o pipeline completo (raw -> refined -> marts) exclusivamente em memória."""
    con = duckdb.connect(":memory:")
    load_raw_layer(con, raw_tables=synthetic_raw_tables)
    transform_refined_layer(con)
    build_marts_layer(con)
    yield con
    con.close()


def test_raw_layer_preserves_untouched_data(
    in_memory_pipeline_db: duckdb.DuckDBPyConnection,
) -> None:
    """Garante que a camada RAW mantém exatamente todas as linhas e formatos de origem (incluindo vírgulas e ruídos)."""
    raw_attr_count = in_memory_pipeline_db.execute(
        "SELECT COUNT(*) FROM raw.atributos_conjuntos"
    ).fetchone()[0]
    assert raw_attr_count == 4

    sample_raw_val = in_memory_pipeline_db.execute(
        "SELECT VlrIndiceEnviado FROM raw.indicadores_continuidade WHERE IdeConjUndConsumidoras = '9001' AND NumPeriodoIndice = '13' AND SigIndicador = 'DEC'"
    ).fetchone()[0]
    assert sample_raw_val == "10,50"


def test_refined_layer_cleans_types_and_deduplicates(
    in_memory_pipeline_db: duckdb.DuckDBPyConnection,
) -> None:
    """Verifica deduplicação, descarte de registros inválidos, conversão de vírgula para float e perfil físico."""
    df_dim = in_memory_pipeline_db.execute(
        "SELECT * FROM refined.dim_conjuntos_eletricos ORDER BY id_conjunto"
    ).df()

    # Eram 4 linhas na raw (1 duplicada e 1 com QtdUCAtendidas = 0) -> devem restar 2 conjuntos válidos
    assert len(df_dim) == 2

    conj_9001 = df_dim[df_dim["id_conjunto"] == "9001"].iloc[0]
    assert conj_9001["sigla_agente"] == "DIST ALFA"
    assert conj_9001["cnpj_agente"] == "11111111000111"
    assert conj_9001["qtd_uc_atendidas"] == 100000  # manteve o registro mais recente (2025-02-01)
    assert conj_9001["densidade_uc_km2"] == pytest.approx(4000.0)
    assert conj_9001["perfil_fisico_conjunto"] == "Urbano Alta Densidade"

    conj_9002 = df_dim[df_dim["id_conjunto"] == "9002"].iloc[0]
    assert conj_9002["densidade_uc_km2"] == pytest.approx(20.0)
    assert conj_9002["perfil_fisico_conjunto"] == "Rural / Rede Extensa"


def test_marts_layer_joins_and_calculates_regulatory_kpis(
    in_memory_pipeline_db: duckdb.DuckDBPyConnection,
) -> None:
    """Valida o JOIN entre as 3 tabelas e os cálculos de transgressão e horas-consumidor na camada MARTS."""
    df_ranking = in_memory_pipeline_db.execute(
        "SELECT * FROM marts.mart_ranking_conjuntos_criticos ORDER BY ranking_criticidade_ano"
    ).df()

    assert len(df_ranking) == 2

    # Conjunto 9001 deve ser o #1 mais crítico: DEC apurado (10.5) > DEC limite (8.0) -> +2.5h * 100.000 UCs = 250.000 UC-horas
    top1 = df_ranking.iloc[0]
    assert top1["id_conjunto"] == "9001"
    assert top1["ranking_criticidade_ano"] == 1
    assert top1["desvio_dec_horas"] == pytest.approx(2.50)
    assert top1["flag_transgressao_dec"] == 1
    assert top1["flag_transgressao_fec"] == 0
    assert top1["uc_horas_excedentes"] == pytest.approx(250000.0)
    assert top1["status_regulatorio"] == "Transgressão de DEC"

    # Conjunto 9002 está dentro da meta (DEC 12.0 <= 15.0 e FEC 8.5 <= 10.0) -> 0 horas excedentes
    top2 = df_ranking.iloc[1]
    assert top2["id_conjunto"] == "9002"
    assert top2["flag_transgressao_dec"] == 0
    assert top2["flag_transgressao_fec"] == 0
    assert top2["uc_horas_excedentes"] == pytest.approx(0.0)
    assert top2["status_regulatorio"] == "Conforme Meta ANEEL"


def test_marts_distributor_aggregation_and_seasonality(
    in_memory_pipeline_db: duckdb.DuckDBPyConnection,
) -> None:
    """Verifica a consolidação por distribuidora e a tabela de evolução mensal."""
    df_dist = in_memory_pipeline_db.execute(
        "SELECT * FROM marts.mart_performance_distribuidoras WHERE sigla_agente = 'DIST ALFA'"
    ).df()

    assert len(df_dist) == 1
    row = df_dist.iloc[0]
    assert row["dec_apurado_ponderado"] == pytest.approx(10.50)
    assert row["dec_limite_ponderado"] == pytest.approx(8.00)
    assert row["indice_severidade_dec"] == pytest.approx(1.313, rel=1e-3)
    assert row["situacao_global_distribuidora"] == "Transgressão Global DEC"

    df_mensal = in_memory_pipeline_db.execute(
        "SELECT * FROM marts.mart_evolucao_continuidade"
    ).df()
    assert len(df_mensal) == 1
    assert df_mensal.iloc[0]["estacao_operacional"] == "Período Chuvoso / Verão"
    assert df_mensal.iloc[0]["dec_mensal_ponderado"] == pytest.approx(1.80)


def test_marts_kpis_globais_precalculated_for_dashboard(
    in_memory_pipeline_db: duckdb.DuckDBPyConnection,
) -> None:
    """Garante que marts.mart_kpis_globais entrega os KPIs prontos sem exigir cálculos no Dashboard."""
    df_global = in_memory_pipeline_db.execute(
        "SELECT * FROM marts.mart_kpis_globais WHERE ano = 2024 AND filtro_distribuidora = 'TODAS'"
    ).df()

    assert len(df_global) == 1
    kpi = df_global.iloc[0]
    assert kpi["total_conjuntos"] == 2
    assert kpi["total_uc_atendidas"] == 120000
    assert kpi["qtd_conjuntos_transgressores_dec"] == 1
    assert kpi["pct_conjuntos_transgressores_dec"] == pytest.approx(50.0)
    assert kpi["total_uc_horas_excedentes"] == pytest.approx(250000.0)

