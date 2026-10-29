-- Camada MARTS: Cruzamento entre Perfil Físico-Elétrico da Rede e Qualidade do Fornecimento
-- Responde à Pergunta 3: Como a densidade de carga e a extensão da rede afetam o DEC e o FEC.

CREATE OR REPLACE TABLE marts.mart_perfil_fisico_qualidade AS
SELECT
    ano,
    perfil_fisico_conjunto,
    COUNT(*) AS qtd_conjuntos,
    SUM(qtd_uc_atendidas) AS total_uc_atendidas,
    ROUND(AVG(densidade_uc_km2), 2) AS densidade_media_uc_km2,
    ROUND(AVG(extensao_rede_km), 2) AS extensao_media_rede_km,
    ROUND(AVG(dec_apurado), 2) AS dec_medio_apurado,
    ROUND(AVG(dec_limite), 2) AS dec_medio_limite,
    ROUND(AVG(desvio_dec_horas), 2) AS desvio_medio_dec_horas,
    ROUND(AVG(razao_severidade_dec), 3) AS severidade_media_dec,
    ROUND(AVG(fec_apurado), 2) AS fec_medio_apurado,
    ROUND(AVG(fec_limite), 2) AS fec_medio_limite,
    ROUND((SUM(flag_transgressao_dec) * 100.0) / COUNT(*), 2) AS taxa_transgressao_dec_pct,
    ROUND((SUM(flag_transgressao_fec) * 100.0) / COUNT(*), 2) AS taxa_transgressao_fec_pct,
    SUM(uc_horas_excedentes) AS total_uc_horas_excedentes
FROM marts.mart_ranking_conjuntos_criticos
GROUP BY ano, perfil_fisico_conjunto
ORDER BY ano DESC, severidade_media_dec DESC;
