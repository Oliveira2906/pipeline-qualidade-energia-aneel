-- Camada MARTS: KPIs Globais Pré-Calculados por Ano (e por Distribuidora)
-- Garante que o Dashboard (Seção 07) leia os cartões de indicadores diretamente da camada marts,
-- sem realizar nenhum cálculo ou agregação na camada de visualização.

CREATE OR REPLACE TABLE marts.mart_kpis_globais AS
SELECT
    ano,
    'TODAS' AS filtro_distribuidora,
    COUNT(DISTINCT sigla_agente) AS qtd_distribuidoras,
    COUNT(*) AS total_conjuntos,
    SUM(qtd_uc_atendidas) AS total_uc_atendidas,
    ROUND(SUM(dec_apurado * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS dec_apurado_ponderado,
    ROUND(SUM(dec_limite * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS dec_limite_ponderado,
    ROUND(
        (SUM(dec_apurado * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0))
        - (SUM(dec_limite * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0)),
        2
    ) AS desvio_dec_ponderado_horas,
    ROUND(SUM(fec_apurado * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS fec_apurado_ponderado,
    ROUND(SUM(fec_limite * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS fec_limite_ponderado,
    SUM(flag_transgressao_dec) AS qtd_conjuntos_transgressores_dec,
    ROUND((SUM(flag_transgressao_dec) * 100.0) / COUNT(*), 2) AS pct_conjuntos_transgressores_dec,
    SUM(flag_transgressao_fec) AS qtd_conjuntos_transgressores_fec,
    ROUND((SUM(flag_transgressao_fec) * 100.0) / COUNT(*), 2) AS pct_conjuntos_transgressores_fec,
    SUM(uc_horas_excedentes) AS total_uc_horas_excedentes
FROM marts.mart_ranking_conjuntos_criticos
GROUP BY ano

UNION ALL

SELECT
    ano,
    sigla_agente AS filtro_distribuidora,
    1 AS qtd_distribuidoras,
    total_conjuntos,
    total_uc_atendidas,
    dec_apurado_ponderado,
    dec_limite_ponderado,
    desvio_dec_ponderado_horas,
    fec_apurado_ponderado,
    fec_limite_ponderado,
    qtd_conjuntos_transgressores_dec,
    pct_conjuntos_transgressores_dec,
    qtd_conjuntos_transgressores_fec,
    pct_conjuntos_transgressores_fec,
    total_uc_horas_excedentes
FROM marts.mart_performance_distribuidoras;
