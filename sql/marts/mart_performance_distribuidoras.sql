-- Camada MARTS: Performance Regulatória Consolidada por Distribuidora e Ano
-- Calcula DEC e FEC médios ponderados por Unidades Consumidoras (metodologia ANEEL),
-- taxa de conjuntos transgressores e volume total de horas-consumidor excedentes.

CREATE OR REPLACE TABLE marts.mart_performance_distribuidoras AS
WITH agregacao_agente AS (
    SELECT
        sigla_agente,
        MAX(cnpj_agente) AS cnpj_agente,
        MAX(uf) AS uf,
        ano,
        COUNT(*) AS total_conjuntos,
        SUM(qtd_uc_atendidas) AS total_uc_atendidas,
        ROUND(SUM(dec_apurado * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS dec_apurado_ponderado,
        ROUND(SUM(dec_limite * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS dec_limite_ponderado,
        ROUND(SUM(fec_apurado * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS fec_apurado_ponderado,
        ROUND(SUM(fec_limite * qtd_uc_atendidas) / NULLIF(SUM(qtd_uc_atendidas), 0), 2) AS fec_limite_ponderado,
        SUM(flag_transgressao_dec) AS qtd_conjuntos_transgressores_dec,
        ROUND((SUM(flag_transgressao_dec) * 100.0) / COUNT(*), 2) AS pct_conjuntos_transgressores_dec,
        SUM(flag_transgressao_fec) AS qtd_conjuntos_transgressores_fec,
        ROUND((SUM(flag_transgressao_fec) * 100.0) / COUNT(*), 2) AS pct_conjuntos_transgressores_fec,
        SUM(uc_horas_excedentes) AS total_uc_horas_excedentes,
        SUM(uc_horas_totais_interrompidas) AS total_uc_horas_interrompidas
    FROM marts.mart_ranking_conjuntos_criticos
    GROUP BY sigla_agente, ano
)
SELECT
    sigla_agente,
    cnpj_agente,
    uf,
    ano,
    total_conjuntos,
    total_uc_atendidas,
    dec_apurado_ponderado,
    dec_limite_ponderado,
    ROUND(dec_apurado_ponderado - dec_limite_ponderado, 2) AS desvio_dec_ponderado_horas,
    ROUND(dec_apurado_ponderado / NULLIF(dec_limite_ponderado, 0), 3) AS indice_severidade_dec,
    fec_apurado_ponderado,
    fec_limite_ponderado,
    ROUND(fec_apurado_ponderado - fec_limite_ponderado, 2) AS desvio_fec_ponderado,
    ROUND(fec_apurado_ponderado / NULLIF(fec_limite_ponderado, 0), 3) AS indice_severidade_fec,
    qtd_conjuntos_transgressores_dec,
    pct_conjuntos_transgressores_dec,
    qtd_conjuntos_transgressores_fec,
    pct_conjuntos_transgressores_fec,
    total_uc_horas_excedentes,
    total_uc_horas_interrompidas,
    CASE
        WHEN dec_apurado_ponderado > dec_limite_ponderado THEN 'Transgressão Global DEC'
        ELSE 'Conforme Global DEC'
    END AS situacao_global_distribuidora
FROM agregacao_agente
ORDER BY ano DESC, indice_severidade_dec DESC;
