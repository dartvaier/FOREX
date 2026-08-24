# FOREX Algorithmic Trading Research Platform

Plataforma de pesquisa e desenvolvimento de estratégias algorítmicas para o mercado Forex, construída em Python e integrada ao MetaTrader 5.

O objetivo do projeto é desenvolver uma infraestrutura confiável para:

- coleta de dados de mercado;
- armazenamento de histórico;
- validação da qualidade dos dados;
- construção de múltiplos timeframes;
- backtesting;
- análise estatística;
- gerenciamento de risco;
- execução em conta demo;
- monitoramento de estratégias.

O projeto é desenvolvido de forma incremental, priorizando integridade dos dados, reprodutibilidade e prevenção de erros como look-ahead bias, uso de candles ainda em formação e modelagem incorreta de custos de execução.

> **Status atual:** infraestrutura de mercado e dados concluída; o Backtest
> Engine baseline está em implementação, com F5.1–F5.13 concluídas.

---

# Status do Projeto

| Fase | Descrição | Status |
|---|---|---|
| F0 | Pesquisa e metodologia | ✅ Concluída |
| F1 | Ambiente de desenvolvimento | ✅ Concluída |
| F2 | Market Data Layer | ✅ Concluída |
| F3 | Historical Data Layer | ✅ Concluída |
| F4 | Data Transformation | ✅ Concluída |
| F5 | Backtest Engine | 🟡 Em andamento (F5.1–F5.13 concluídas) |
| F6 | Strategy Engine | ⬜ Não iniciada |
| F7 | Risk Engine | ⬜ Não iniciada |
| F8 | Execution Engine | ⬜ Não iniciada |
| F9 | Validação em conta Demo | ⬜ Não iniciada |

---

# Stack

O projeto atualmente utiliza:

- Windows
- Python 3.14.5
- MetaTrader 5
- MetaTrader5 Python API
- pandas
- NumPy
- PyArrow
- python-dotenv
- matplotlib
- pytest
- Git

Versão validada do pacote MetaTrader5 durante o desenvolvimento:

```text
MetaTrader5 5.0.6090
Mercado Inicial
O primeiro mercado utilizado no desenvolvimento é:
Mercado: Forex
Símbolo: EURUSD
Fonte inicial: MetaQuotes-Demo
Especificações observadas para o EURUSD:
Digits:        5
Point:         0.00001
Pip:           0.00010
Points / Pip:  10

Contract Size: 100000

Volume mínimo: 0.01
Volume step:   0.01
Esses valores são obtidos dinamicamente através do MetaTrader 5 e não devem ser tratados como universais para todos os símbolos.
Arquitetura Atual
A arquitetura implementada até o momento é:
                    MetaTrader 5
                         │
                         ▼
                     MT5Client
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
         MarketData           HistoricalData
              │                     │
              │                     ▼
              │                  Parquet
              │                     │
              └──────────┬──────────┘
                         │
                         ▼
                 TimeframeBuilder
                         │
                 ┌───────┴───────┐
                 ▼               ▼
                H1              H4
Componentes ainda planejados:
BacktestEngine
Strategy Engine
CostModel
Risk Engine
Execution Engine
Monitoring
Estrutura do Projeto
Estrutura principal:
FOREX/
│
├── broker/
│   ├── __init__.py
│   └── mt5_client.py
│
├── data/
│   ├── __init__.py
│   ├── market_data.py
│   ├── historical_data.py
│   ├── timeframe_builder.py
│   │
│   ├── raw/
│   │   └── EURUSD/
│   │       └── M15.parquet
│   │
│   ├── processed/
│   │   └── EURUSD/
│   │       ├── H1.parquet
│   │       └── H4.parquet
│   │
│   └── metadata/
│       └── EURUSD_M15.json
│
├── strategy/
├── risk/
├── execution/
├── backtest/
├── monitoring/
├── config/
│
├── tests/
│   ├── test_market_data.py
│   ├── test_historical_data.py
│   └── test_timeframe_builder.py
│
├── docs/
│
├── main.py
├── collect_history.py
├── analyze_history.py
├── build_timeframes.py
├── generate_metadata.py
│
├── pytest.ini
├── requirements.txt
├── .env
├── .gitignore
│
├── DECISIONS.md
├── CHANGELOG.md
└── README.md
Timezone
Todo o sistema utiliza:
UTC
como timezone interno.
Isso inclui:
candles;
ticks;
histórico;
datasets processados;
timestamps utilizados pelo backtester.
Conversões para sessões específicas só devem ocorrer quando uma estratégia realmente precisar delas.
Exemplos:
Europe/London
America/New_York
Essa decisão reduz problemas relacionados a timezone local e horário de verão.
Candles Fechados
A estratégia nunca deve receber deliberadamente um candle ainda em formação.
No MetaTrader 5:
posição 0 = barra mais recente/corrente
posição 1 = barra anterior
A camada MarketData utiliza somente candles fechados para os dados destinados às estratégias.
Existe um teste automatizado específico para garantir esse comportamento:
test_closed_bars_do_not_include_current_bar
Isso é uma proteção contra look-ahead e contra alterações futuras acidentais na camada de mercado.
Dataset Histórico Principal
Dataset bruto atual:
Símbolo:    EURUSD
Timeframe:  M15
Fonte:      MetaQuotes-Demo
Formato:    Parquet
Timezone:   UTC
Período disponível:
Primeiro candle:
2015-01-02 09:00:00 UTC

Último candle:
2026-08-07 23:45:00 UTC
Quantidade:
288223 candles M15
Arquivo:
data/raw/EURUSD/M15.parquet
Qualidade do Dataset M15
A auditoria atual encontrou:
Duplicados:       0
Valores nulos:    0
OHLC inválidos:   0

Gaps totais:      659
Weekend gaps:     605
Intraweek gaps:    54
A maior parte dos gaps está relacionada ao fechamento semanal ou a períodos especiais como Natal e Ano Novo.
Alguns gaps intraweek não possuem classificação definitiva e são preservados no dataset.
Regra importante
Gaps não são preenchidos artificialmente.
Não são utilizados métodos como:
ffill()
para fabricar candles inexistentes.
A descontinuidade original dos dados é preservada.
Spread Histórico
O campo spread presente nos candles do MetaTrader 5 foi considerado inconsistente para modelagem direta de custos.
Foi observada uma quantidade significativa de:
spread = 0
e mudanças relevantes na distribuição do campo entre diferentes anos.
Portanto:
spread dos candles != CostModel oficial
O futuro Backtest Engine deverá possuir um modelo de custos independente.
Exemplos planejados:
FixedSpreadModel
ConservativeSpreadModel
TickBidAskModel
BrokerHistoricalCostModel
Isso permitirá também realizar stress tests de custos.
Tick Volume e Real Volume
Tick Volume
O campo:
tick_volume
é preservado e pode ser utilizado futuramente como medida de atividade relativa.
Ele não deve ser interpretado como o volume global negociado no mercado Forex.
Real Volume
O campo:
real_volume
apresentou inconsistência estrutural ao longo do histórico.
Percentual de candles com real_volume > 0:
2015  ~44%
2016 ~100%
2017  ~43%
2018+   0%
Por esse motivo:
real_volume não será utilizado como feature
O campo continua preservado no dataset bruto apenas para rastreabilidade.
Timeframes Derivados
Os timeframes superiores são construídos a partir do M15.
M15
 │
 ├── H1
 │
 └── H4
Não são tratados como fontes independentes nesta etapa.
H1
Arquivo:
data/processed/EURUSD/H1.parquet
Resultado:
Candles:       72080
Completos:     72018
Incompletos:      62

Primeiro:
2015-01-02 09:00 UTC

Último:
2026-08-07 23:00 UTC
Cada H1 completo deve possuir:
4 candles M15
H4
Arquivo:
data/processed/EURUSD/H4.parquet
Resultado:
Candles:       18046
Completos:     17929
Incompletos:     117

Primeiro:
2015-01-02 08:00 UTC

Último:
2026-08-07 20:00 UTC
Cada H4 completo deve possuir:
16 candles M15
Candles Incompletos
Candles incompletos não são apagados durante a transformação.
São armazenados com informações como:
source_bar_count
expected_bar_count
complete
Exemplo:
H1

source_bar_count   = 3
expected_bar_count = 4
complete           = False
A intenção é preservar informações sobre defeitos e gaps do dataset.
Entretanto, estratégias e backtests deverão trabalhar apenas com:
complete == True
salvo quando houver motivo explícito para comportamento diferente.
Testes Automatizados
O projeto atualmente possui:
25 testes
25 passed
0 failed
Executados com:
pytest -v
As principais áreas testadas são:
Market Data
conexão lógica com os dados do MT5;
Bid e Ask válidos;
candles fechados;
ordenação temporal;
timestamps únicos;
UTC;
integridade OHLC;
preços positivos;
tick volume não negativo;
proteção contra candle corrente.
Historical Data
existência do dataset;
dataset não vazio;
timestamps únicos;
ordenação;
UTC;
ausência de valores nulos;
integridade OHLC;
preços positivos.
Timeframe Builder
criação de H1;
criação de H4;
H1 completo possui 4 candles M15;
H4 completo possui 16 candles M15;
alinhamento temporal H1;
alinhamento temporal H4;
UTC preservado;
integridade OHLC após resample.
Ambiente
Criação do ambiente virtual:
python -m venv .venv
Ativação no Windows PowerShell:
.venv\Scripts\activate
Instalação das principais dependências:
pip install MetaTrader5 pandas numpy python-dotenv matplotlib pytest pyarrow
Atualização do arquivo de dependências:
pip freeze > requirements.txt
MetaTrader 5
O MetaTrader 5 precisa estar instalado e disponível no Windows.
A integração atualmente utiliza o terminal já autenticado.
Não é necessário armazenar login e senha dentro do código nesta etapa.
O MT5Client é responsável pelo ciclo:
initialize
    ↓
operações read-only
    ↓
shutdown
Segurança
O projeto ainda não possui execução de ordens.
Nesta fase:
TRADING_ENABLED=false
A infraestrutura atual é destinada a:
coleta
análise
pesquisa
backtest futuro
Nenhuma estratégia deve operar capital real durante as fases atuais do projeto.
Antes de qualquer execução futura deverão existir, no mínimo:
validação em backtest;
validação out-of-sample;
testes de custos;
gerenciamento de risco;
limites de perda;
kill switch;
validação em conta demo.
Metodologia
O desenvolvimento das estratégias é separado da infraestrutura.
A metodologia quantitativa do projeto está documentada separadamente no material de pesquisa do projeto.
O princípio central é:
Hipótese
   ↓
Especificação prévia
   ↓
Backtest
   ↓
Robustez
   ↓
Out-of-sample
   ↓
Demo
   ↓
Execução futura
Não será considerada válida uma estratégia apenas por apresentar bom resultado em um único backtest.
Próxima Fase
A próxima fase do projeto será:
F5 — Backtest Engine
O Backtest Engine deverá ser projetado antes da implementação das estratégias.
Entre suas responsabilidades futuras estarão:
controle temporal
execução bar-by-bar
posição
entradas e saídas
PnL
custos
spread
slippage
equity
trades
métricas
logs
A estratégia não deverá controlar diretamente execução ou gerenciamento de risco.
Arquitetura pretendida:
                  Market Data
                       │
                       ▼
                  BacktestEngine
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Strategy       Risk       CostModel
          │            │            │
          └────────────┼────────────┘
                       ▼
                     Trade
                       │
                       ▼
                  Performance
Documentação
A documentação detalhada está disponível em:
docs/
Arquivos planejados:
01_PROJECT_OVERVIEW.md
02_ARCHITECTURE.md
03_ENVIRONMENT_SETUP.md
04_MT5_INTEGRATION.md
05_MARKET_DATA.md
06_HISTORICAL_DATA.md
07_DATA_QUALITY.md
08_TESTING.md
09_DATA_TRANSFORMATION.md
10_BACKTEST_DESIGN.md
11_ROADMAP.md
Decisões arquiteturais importantes são registradas em:
DECISIONS.md
O histórico de mudanças é mantido em:
CHANGELOG.md
