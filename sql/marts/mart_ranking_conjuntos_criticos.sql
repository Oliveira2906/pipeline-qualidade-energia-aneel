-- Camada MARTS: Ranking de Conjuntos Elétricos Críticos e Impacto ao Consumidor
-- Realiza JOIN entre indicadores apurados anuais, limites regulatórios ANEEL e atributos físico-elétricos.

CREATE OR REPLACE TABLE marts.mart_ranking_conjuntos_criticos AS
WITH base_joined AS (
    SELECT
        ap.id_conjunto,
        dim.nome_conjunto,
        dim.sigla_agente,
        dim.cnpj_agente,
        dim.uf,
        ap.ano,
        dim.qtd_uc_atendidas,
        dim.area_conjunto_km2,
        dim.extensao_rede_km,
        dim.qtd_subestacoes,
        dim.densidade_uc_km2,
        dim.densidade_uc_km_rede,
        dim.perfil_fisico_conjunto,
        ap.dec_apurado,
        lim.dec_limite,
        ROUND(ap.dec_apurado - lim.dec_limite, 2) AS desvio_dec_horas,
        ROUND(ap.dec_apurado / NULLIF(lim.dec_limite, 0), 3) AS razao_severidade_dec,
        ROUND(((ap.dec_apurado - lim.dec_limite) / NULLIF(lim.dec_limite, 0)) * 100.0, 2) AS pct_desvio_dec,
        ap.fec_apurado,
        lim.fec_limite,
        ROUND(ap.fec_apurado - lim.fec_limite, 2) AS desvio_fec,
        ROUND(ap.fec_apurado / NULLIF(lim.fec_limite, 0), 3) AS razao_severidade_fec,
        ROUND(((ap.fec_apurado - lim.fec_limite) / NULLIF(lim.fec_limite, 0)) * 100.0, 2) AS pct_desvio_fec,
        CASE WHEN ap.dec_apurado > lim.dec_limite THEN 1 ELSE 0 END AS flag_transgressao_dec,
        CASE WHEN ap.fec_apurado > lim.fec_limite THEN 1 ELSE 0 END AS flag_transgressao_fec,
        CASE
            WHEN ap.dec_apurado > lim.dec_limite AND ap.fec_apurado > lim.fec_limite THEN 1
            ELSE 0
        END AS flag_transgressao_ambos,
        ROUND(GREATEST(0.0, ap.dec_apurado - lim.dec_limite) * dim.qtd_uc_atendidas, 0) AS uc_horas_excedentes,
        ROUND(ap.dec_apurado * dim.qtd_uc_atendidas, 0) AS uc_horas_totais_interrompidas,
        CASE
            WHEN ap.dec_apurado > lim.dec_limite AND ap.fec_apurado > lim.fec_limite THEN 'Crítico (DEC e FEC Violados)'
            WHEN ap.dec_apurado > lim.dec_limite THEN 'Transgressão de DEC'
            WHEN ap.fec_apurado > lim.fec_limite THEN 'Transgressão de FEC'
            ELSE 'Conforme Meta ANEEL'
        END AS status_regulatorio
    FROM refined.fato_continuidade_apurada AS ap
    INNER JOIN refined.fato_limites_regulatorios AS lim
        ON ap.id_conjunto = lim.id_conjunto
       AND ap.ano = lim.ano
    INNER JOIN refined.dim_conjuntos_eletricos AS dim
        ON ap.id_conjunto = dim.id_conjunto
       AND ap.ano = dim.ano
    WHERE ap.tipo_periodo = 'ANUAL'
)
SELECT
    *,
    RANK() OVER (
        PARTITION BY ano
        ORDER BY uc_horas_excedentes DESC, razao_severidade_dec DESC
    ) AS ranking_criticidade_ano
FROM base_joined;
