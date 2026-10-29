# Pipeline de Qualidade da Distribuição de Energia Elétrica (ANEEL — DEC & FEC)

> **O Desafio Final: O Seu Pipeline, do Zero**  
> Engenharia de Dados ponta a ponta com **Python, SQL (DuckDB), IA, Testes Unitários (`pytest`), Git e Streamlit**.

---

## 1. Contexto e Fonte de Dados

Este projeto constrói um pipeline analítico completo sobre dados públicos oficiais do **Portal de Dados Abertos da ANEEL** (*Agência Nacional de Energia Elétrica*), avaliando a **Continuidade do Serviço de Distribuição de Energia Elétrica** no Brasil por meio dos indicadores coletivos **DEC** e **FEC**:

* **DEC (*Duração Equivalente de Interrupção por Unidade Consumidora*):** Tempo médio (em horas) em que uma unidade consumidora ficou sem energia elétrica no período apurado.
* **FEC (*Frequência Equivalente de Interrupção por Unidade Consumidora*):** Número médio de interrupções sofridas por unidade consumidora no período apurado.

### Tabelas Relacionadas na Origem

O pipeline extrai e integra **3 tabelas oficiais** conectadas pelas chaves `IdeConjUndConsumidoras` (Identificador do Conjunto Elétrico), `SigAgente` (Distribuidora) e `AnoIndice` (Ano de Apuração):

1. `raw.indicadores_continuidade`: Séries apuradas de DEC e FEC enviadas pelas distribuidoras para cada conjunto elétrico.
2. `raw.limites_continuidade`: Limites regulatórios máximos de DEC e FEC homologados pela ANEEL para cada conjunto e ano.
3. `raw.atributos_conjuntos`: Atributos físico-elétricos de cada conjunto (unidades consumidoras atendidas, extensão de rede, área territorial e subestações).

---

## 2. As Perguntas de Negócio que o Dado Responde

1. **Conformidade Regulatória das Distribuidoras:** Quais distribuidoras possuem o maior percentual de conjuntos elétricos violando os limites anuais de DEC e FEC definidos pela ANEEL, e qual o **Índice de Severidade Regulatória** ($\text{DEC}_{\text{apurado}} / \text{DEC}_{\text{limite}}$)?
2. **Impacto Real ao Consumidor (Consumidor × Horas sem Energia):** Quais conjuntos elétricos concentram o maior volume de **horas-consumidor perdidas acima da meta regulatória** ($\max(0, \text{DEC}_{\text{apurado}} - \text{DEC}_{\text{limite}}) \times \text{UCs Atendidas}$)?
3. **Perfil Físico-Elétrico × Confiabilidade da Rede:** Como a densidade elétrica (UCs por $\text{km}^2$ e porte do conjunto) se relaciona com o estouro de DEC (tempo de reparo/deslocamento) vs. FEC (frequência de falhas)?
4. **Trajetória e Evolução Regulatória:** Como evoluiu a qualidade do fornecimento entre os anos analisados e quais concessionárias apresentaram melhora ou degradação nos indicadores?

---

## 3. Arquitetura em 3 Camadas (`raw`, `refined`, `marts`)

* **`raw` (Dado Bruto Intocado):** Tabelas carregadas exatamente como vêm da origem (strings originais, decimais com vírgula no padrão brasileiro, sem filtros).
* **`refined` (Dado Limpo e Tipado):** Conversão de tipos (`VARCHAR` com vírgula para `DOUBLE`), padronização de siglas e chaves, deduplicação, filtragem de inconsistências e pivotagem de DEC/FEC.
* **`marts` (Indicadores de Negócio):** Tabelas consolidadas com `JOIN` entre apurado, limites e atributos físico-elétricos, prontas para leitura direta pelo Dashboard e pelo módulo de IA (zero cálculo na camada de visualização).
