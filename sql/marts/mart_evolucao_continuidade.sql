-- Camada MARTS: Evolução Mensal e Sazonalidade da Continuidade por Distribuidora
-- Responde à Pergunta 4: Impacto sazonal (verão chuvoso vs período seco) e trajetória histórica.

CREATE OR REPLACE TABLE marts.mart_evolucao_continuidade AS
SELECT
    ap.ano,
    ap.periodo_indice AS mes,
    CASE ap.periodo_indice
        WHEN 1 THEN '01 - Jan'
        WHEN 2 THEN '02 - Fev'
        WHEN 3 THEN '03 - Mar'
        WHEN 4 THEN '04 - Abr'
        WHEN 5 THEN '05 - Mai'
        WHEN 6 THEN '06 - Jun'
        WHEN 7 THEN '07 - Jul'
        WHEN 8 THEN '08 - Ago'
        WHEN 9 THEN '09 - Set'
        WHEN 10 THEN '10 - Out'
        WHEN 11 THEN '11 - Nov'
        WHEN 12 THEN '12 - Dez'
    END AS nome_mes,
    CASE
        WHEN ap.periodo_indice IN (1, 2, 3, 11, 12) THEN 'Período Chuvoso / Verão'
        ELSE 'Período Seco / Amenizado'
    END AS estacao_operacional,
    dim.sigla_agente,
    dim.uf,
    COUNT(DISTINCT ap.id_conjunto) AS qtd_conjuntos,
    SUM(dim.qtd_uc_atendidas) AS total_uc_atendidas,
    ROUND(SUM(ap.dec_apurado * dim.qtd_uc_atendidas) / NULLIF(SUM(dim.qtd_uc_atendidas), 0), 2) AS dec_mensal_ponderado,
    ROUND(SUM((lim.dec_limite / 12.0) * dim.qtd_uc_atendidas) / NULLIF(SUM(dim.qtd_uc_atendidas), 0), 2) AS referencia_mensal_limite_dec,
    ROUND(SUM(ap.fec_apurado * dim.qtd_uc_atendidas) / NULLIF(SUM(dim.qtd_uc_atendidas), 0), 2) AS fec_mensal_ponderado
FROM refined.fato_continuidade_apurada AS ap
INNER JOIN refined.dim_conjuntos_eletricos AS dim
    ON ap.id_conjunto = dim.id_conjunto
   AND ap.ano = dim.ano
INNER JOIN refined.fato_limites_regulatorios AS lim
    ON ap.id_conjunto = lim.id_conjunto
   AND ap.ano = lim.ano
WHERE ap.tipo_periodo = 'MENSAL'
GROUP BY ap.ano, ap.periodo_indice, dim.sigla_agente, dim.uf
ORDER BY ap.ano, ap.periodo_indice, dim.sigla_agente;
