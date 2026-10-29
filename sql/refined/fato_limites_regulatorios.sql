-- Camada REFINED: Fato de Limites Regulatórios Anuais (DEC e FEC) homologados pela ANEEL
-- Deduplica registros por conjunto/ano/indicador e pivota DEC e FEC em colunas numéricas.

CREATE OR REPLACE TABLE refined.fato_limites_regulatorios AS
WITH limites_limpos AS (
    SELECT
        TRIM(IdeConjUndConsumidoras) AS id_conjunto,
        UPPER(TRIM(SigAgente)) AS sigla_agente,
        UPPER(TRIM(SigIndicador)) AS sigla_indicador,
        TRY_CAST(TRIM(AnoLimite) AS INTEGER) AS ano,
        TRY_CAST(REPLACE(TRIM(VlrLimiteEnviado), ',', '.') AS DOUBLE) AS valor_limite,
        TRY_CAST(TRIM(DatGeracaoConjuntoDados) AS DATE) AS data_geracao
    FROM raw.limites_continuidade
    WHERE TRIM(IdeConjUndConsumidoras) IS NOT NULL
      AND UPPER(TRIM(SigIndicador)) IN ('DEC', 'FEC')
      AND TRY_CAST(REPLACE(TRIM(VlrLimiteEnviado), ',', '.') AS DOUBLE) > 0
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY TRIM(IdeConjUndConsumidoras), TRY_CAST(TRIM(AnoLimite) AS INTEGER), UPPER(TRIM(SigIndicador))
        ORDER BY DatGeracaoConjuntoDados DESC
    ) = 1
)
SELECT
    id_conjunto,
    MAX(sigla_agente) AS sigla_agente,
    ano,
    ROUND(MAX(CASE WHEN sigla_indicador = 'DEC' THEN valor_limite END), 2) AS dec_limite,
    ROUND(MAX(CASE WHEN sigla_indicador = 'FEC' THEN valor_limite END), 2) AS fec_limite,
    MAX(data_geracao) AS data_geracao
FROM limites_limpos
GROUP BY id_conjunto, ano
HAVING dec_limite IS NOT NULL AND fec_limite IS NOT NULL;
