-- Camada REFINED: Fato de Indicadores de Continuidade Apurados (DEC e FEC)
-- Trata decimais brasileiros, remove valores negativos/inválidos, deduplica e pivota DEC e FEC.

CREATE OR REPLACE TABLE refined.fato_continuidade_apurada AS
WITH apurados_limpos AS (
    SELECT
        TRIM(IdeConjUndConsumidoras) AS id_conjunto,
        UPPER(TRIM(DscConjUndConsumidoras)) AS nome_conjunto,
        UPPER(TRIM(SigAgente)) AS sigla_agente,
        REGEXP_REPLACE(TRIM(NumCNPJ), '[^0-9]', '', 'g') AS cnpj_agente,
        UPPER(TRIM(SigIndicador)) AS sigla_indicador,
        TRY_CAST(TRIM(AnoIndice) AS INTEGER) AS ano,
        TRY_CAST(TRIM(NumPeriodoIndice) AS INTEGER) AS periodo_indice,
        TRY_CAST(REPLACE(TRIM(VlrIndiceEnviado), ',', '.') AS DOUBLE) AS valor_apurado,
        TRY_CAST(TRIM(DatGeracaoConjuntoDados) AS DATE) AS data_geracao
    FROM raw.indicadores_continuidade
    WHERE TRIM(IdeConjUndConsumidoras) IS NOT NULL
      AND UPPER(TRIM(SigIndicador)) IN ('DEC', 'FEC')
      AND TRY_CAST(REPLACE(TRIM(VlrIndiceEnviado), ',', '.') AS DOUBLE) >= 0
      AND TRY_CAST(TRIM(NumPeriodoIndice) AS INTEGER) BETWEEN 1 AND 13
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY
            TRIM(IdeConjUndConsumidoras),
            TRY_CAST(TRIM(AnoIndice) AS INTEGER),
            TRY_CAST(TRIM(NumPeriodoIndice) AS INTEGER),
            UPPER(TRIM(SigIndicador))
        ORDER BY DatGeracaoConjuntoDados DESC
    ) = 1
)
SELECT
    id_conjunto,
    MAX(nome_conjunto) AS nome_conjunto,
    MAX(sigla_agente) AS sigla_agente,
    MAX(cnpj_agente) AS cnpj_agente,
    ano,
    periodo_indice,
    CASE
        WHEN periodo_indice = 13 THEN 'ANUAL'
        ELSE 'MENSAL'
    END AS tipo_periodo,
    ROUND(MAX(CASE WHEN sigla_indicador = 'DEC' THEN valor_apurado END), 2) AS dec_apurado,
    ROUND(MAX(CASE WHEN sigla_indicador = 'FEC' THEN valor_apurado END), 2) AS fec_apurado,
    MAX(data_geracao) AS data_geracao
FROM apurados_limpos
GROUP BY id_conjunto, ano, periodo_indice
HAVING dec_apurado IS NOT NULL AND fec_apurado IS NOT NULL;
