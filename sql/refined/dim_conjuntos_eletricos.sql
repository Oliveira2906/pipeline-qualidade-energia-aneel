-- Camada REFINED: Dimensão de Conjuntos Elétricos e Atributos Físico-Elétricos
-- Limpa strings, converte decimais do padrão brasileiro (vírgula -> ponto),
-- deduplica envios e classifica o perfil físico-elétrico da rede.

CREATE OR REPLACE TABLE refined.dim_conjuntos_eletricos AS
WITH base_dedup AS (
    SELECT
        TRIM(IdeConjUndConsumidoras) AS id_conjunto,
        UPPER(TRIM(DscConjUndConsumidoras)) AS nome_conjunto,
        UPPER(TRIM(SigAgente)) AS sigla_agente,
        REGEXP_REPLACE(TRIM(NumCNPJ), '[^0-9]', '', 'g') AS cnpj_agente,
        UPPER(TRIM(SigUF)) AS uf,
        TRY_CAST(TRIM(AnoIndice) AS INTEGER) AS ano,
        TRY_CAST(TRIM(QtdUCAtendidas) AS BIGINT) AS qtd_uc_atendidas,
        TRY_CAST(REPLACE(TRIM(VlrAreaConjuntoKm2), ',', '.') AS DOUBLE) AS area_conjunto_km2,
        TRY_CAST(REPLACE(TRIM(VlrExtensaoRedeKm), ',', '.') AS DOUBLE) AS extensao_rede_km,
        TRY_CAST(TRIM(QtdSubestacoes) AS INTEGER) AS qtd_subestacoes,
        TRY_CAST(TRIM(DatGeracaoConjuntoDados) AS DATE) AS data_geracao
    FROM raw.atributos_conjuntos
    WHERE TRIM(IdeConjUndConsumidoras) IS NOT NULL
      AND TRY_CAST(TRIM(AnoIndice) AS INTEGER) IS NOT NULL
      AND TRY_CAST(TRIM(QtdUCAtendidas) AS BIGINT) > 0
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY TRIM(IdeConjUndConsumidoras), TRY_CAST(TRIM(AnoIndice) AS INTEGER)
        ORDER BY DatGeracaoConjuntoDados DESC
    ) = 1
)
SELECT
    id_conjunto,
    nome_conjunto,
    sigla_agente,
    cnpj_agente,
    uf,
    ano,
    qtd_uc_atendidas,
    ROUND(area_conjunto_km2, 2) AS area_conjunto_km2,
    ROUND(extensao_rede_km, 2) AS extensao_rede_km,
    qtd_subestacoes,
    ROUND(qtd_uc_atendidas / NULLIF(area_conjunto_km2, 0), 2) AS densidade_uc_km2,
    ROUND(qtd_uc_atendidas / NULLIF(extensao_rede_km, 0), 2) AS densidade_uc_km_rede,
    CASE
        WHEN (qtd_uc_atendidas / NULLIF(area_conjunto_km2, 0)) >= 2000 THEN 'Urbano Alta Densidade'
        WHEN (qtd_uc_atendidas / NULLIF(area_conjunto_km2, 0)) >= 500 THEN 'Urbano / Metropolitano'
        WHEN (qtd_uc_atendidas / NULLIF(area_conjunto_km2, 0)) >= 100 THEN 'Misto / Regional'
        ELSE 'Rural / Rede Extensa'
    END AS perfil_fisico_conjunto,
    data_geracao
FROM base_dedup;
