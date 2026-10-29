"""Módulo de transformação da camada RAW para a camada REFINED (limpeza, tipagem e deduplicação)."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/aneel_continuidade.duckdb")
SQL_REFINED_DIR = Path(__file__).resolve().parent.parent / "sql" / "refined"

REFINED_STEPS = [
    ("dim_conjuntos_eletricos", "dim_conjuntos_eletricos.sql"),
    ("fato_limites_regulatorios", "fato_limites_regulatorios.sql"),
    ("fato_continuidade_apurada", "fato_continuidade_apurada.sql"),
]


def transform_refined_layer(
    con: duckdb.DuckDBPyConnection,
    sql_dir: Path = SQL_REFINED_DIR,
) -> dict[str, int]:
    """Executa os scripts SQL da camada `refined` sobre uma conexão DuckDB aberta."""
    con.execute("CREATE SCHEMA IF NOT EXISTS refined;")
    row_counts: dict[str, int] = {}

    for table_name, sql_filename in REFINED_STEPS:
        sql_path = sql_dir / sql_filename
        query = sql_path.read_text(encoding="utf-8")
        con.execute(query)
        count = con.execute(f"SELECT COUNT(*) FROM refined.{table_name}").fetchone()[0]
        row_counts[f"refined.{table_name}"] = int(count)
        logger.info("Tabela refined.%s transformada com %d registros limpos.", table_name, count)

    return row_counts


def run_transform_refined(db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    """Abre o banco DuckDB do projeto e executa a camada `refined`."""
    with duckdb.connect(str(db_path)) as con:
        return transform_refined_layer(con)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    counts = run_transform_refined()
    print("Camada REFINED processada com sucesso:", counts)
