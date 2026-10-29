"""Orquestrador ponta a ponta do pipeline de Continuidade da Distribuição (ANEEL).

Executa sequencialmente:
1. Camada RAW (`raw.*`) — dados brutos intocados da origem ANEEL.
2. Camada REFINED (`refined.*`) — limpeza, conversão de tipos decimais BR e deduplicação.
3. Camada MARTS (`marts.*`) — JOINs entre apurado, limites e atributos físicos + indicadores regulatórios.
4. Módulo de IA (`marts.mart_parecer_executivo_ia`) — síntese executiva sobre a camada marts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb

from src.ai_insights import generate_ai_executive_summary
from src.build_marts import build_marts_layer
from src.extract_raw import DEFAULT_DB_PATH, load_raw_layer
from src.transform_refined import transform_refined_layer

logger = logging.getLogger(__name__)


def run_full_pipeline(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Executa todas as etapas do pipeline no banco DuckDB informado."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        raw_counts = load_raw_layer(con)
        refined_counts = transform_refined_layer(con)
        marts_counts = build_marts_layer(con)
        parecer = generate_ai_executive_summary(con, ano_ref=2024)

    return {
        "raw": raw_counts,
        "refined": refined_counts,
        "marts": marts_counts,
        "parecer_preview": parecer[:240] + "...",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    summary = run_full_pipeline()
    print("\n=== PIPELINE ANEEL EXECUTADO COM SUCESSO ===")
    for layer in ("raw", "refined", "marts"):
        print(f"\nCamada {layer.upper()}:")
        for tbl, cnt in summary[layer].items():
            print(f"  - {tbl}: {cnt} linhas")
