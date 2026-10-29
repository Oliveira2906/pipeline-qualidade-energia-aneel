"""Módulo de construção da camada MARTS (Indicadores de Negócio e JOINs entre tabelas)."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/aneel_continuidade.duckdb")
SQL_MARTS_DIR = Path(__file__).resolve().parent.parent / "sql" / "marts"

MARTS_STEPS = [
    ("mart_ranking_conjuntos_criticos", "mart_ranking_conjuntos_criticos.sql"),
    ("mart_performance_distribuidoras", "mart_performance_distribuidoras.sql"),
    ("mart_kpis_globais", "mart_kpis_globais.sql"),
    ("mart_perfil_fisico_qualidade", "mart_perfil_fisico_qualidade.sql"),
    ("mart_evolucao_continuidade", "mart_evolucao_continuidade.sql"),
]


def build_marts_layer(
    con: duckdb.DuckDBPyConnection,
    sql_dir: Path = SQL_MARTS_DIR,
) -> dict[str, int]:
    """Executa os scripts SQL da camada `marts` sobre uma conexão DuckDB aberta."""
    con.execute("CREATE SCHEMA IF NOT EXISTS marts;")
    row_counts: dict[str, int] = {}

    for table_name, sql_filename in MARTS_STEPS:
        sql_path = sql_dir / sql_filename
        query = sql_path.read_text(encoding="utf-8")
        con.execute(query)
        count = con.execute(f"SELECT COUNT(*) FROM marts.{table_name}").fetchone()[0]
        row_counts[f"marts.{table_name}"] = int(count)
        logger.info("Tabela marts.%s construída com %d registros de indicadores.", table_name, count)

    return row_counts


def run_build_marts(db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    """Abre o banco DuckDB do projeto e constrói todas as tabelas da camada `marts`."""
    with duckdb.connect(str(db_path)) as con:
        return build_marts_layer(con)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    counts = run_build_marts()
    print("Camada MARTS construída com sucesso:", counts)
