# Environment Setup

## 1. Objetivo

Este documento descreve como preparar o ambiente de desenvolvimento da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo é permitir que o projeto possa ser reproduzido em outra máquina Windows com o mínimo possível de ambiguidade.

O ambiente atual foi validado com:

```text
Operating System: Windows
Python:           3.14.5
MetaTrader5:      5.0.6090
pytest:           9.1.1
```

O projeto utiliza atualmente o MetaTrader 5 instalado localmente e integrado ao Python através do pacote oficial `MetaTrader5`.

---

# 2. Requisitos

Antes de iniciar, a máquina deve possuir:

```text
Windows
Python
Git
MetaTrader 5
VS Code ou editor equivalente
```

A configuração atual foi construída e validada utilizando Windows nativo.

A integração Python ↔ MetaTrader 5 também ocorre nativamente no Windows.

---

# 3. Diretório do Projeto

O diretório utilizado no ambiente atual é:

```text
C:\Users\Gabriel\Desktop\FOREX
```

O projeto não deve depender desse caminho específico.

Em outra máquina pode ser utilizado qualquer diretório apropriado.

Exemplo:

```text
C:\Projects\FOREX
```

ou:

```text
D:\Development\FOREX
```

---

# 4. Verificar Python

No PowerShell:

```powershell
python --version
```

Ambiente atualmente validado:

```text
Python 3.14.5
```

Também é possível verificar:

```powershell
where.exe python
```

Isso ajuda a identificar qual instalação do Python está sendo utilizada.

---

# 5. Verificar pip

Execute:

```powershell
pip --version
```

ou preferencialmente:

```powershell
python -m pip --version
```

Usar:

```text
python -m pip
```

reduz o risco de utilizar um `pip` associado a outra instalação do Python.

---

# 6. Verificar Git

Execute:

```powershell
git --version
```

O ambiente utilizado durante o desenvolvimento possuía:

```text
git version 2.54.0.windows.1
```

A versão exata do Git não é considerada uma dependência lógica do sistema.

---

# 7. Criar Ambiente Virtual

Na raiz do projeto:

```powershell
python -m venv .venv
```

Isso cria:

```text
FOREX/
└── .venv/
```

O ambiente virtual mantém as dependências do projeto isoladas da instalação global do Python.

---

# 8. Ativar Ambiente Virtual

No PowerShell:

```powershell
.venv\Scripts\activate
```

Quando ativado, o terminal deverá mostrar algo semelhante a:

```text
(.venv) PS C:\...\FOREX>
```

Todos os comandos relacionados ao projeto devem ser executados preferencialmente com a `.venv` ativa.

---

# 9. Verificar Python da .venv

Com o ambiente ativado:

```powershell
python -c "import sys; print(sys.executable)"
```

O resultado deve apontar para algo semelhante a:

```text
...\FOREX\.venv\Scripts\python.exe
```

Isso confirma que o Python utilizado pertence ao ambiente virtual.

---

# 10. Atualizar pip

Com a `.venv` ativa:

```powershell
python -m pip install --upgrade pip
```

Durante a configuração inicial foram observados avisos relacionados ao cache do pip:

```text
WARNING: Cache entry deserialization failed, entry ignored
```

Como a instalação das dependências foi concluída normalmente, esses avisos não impediram o funcionamento do ambiente.

---

# 11. Dependências Principais

As dependências atualmente utilizadas incluem:

```text
MetaTrader5
pandas
numpy
python-dotenv
matplotlib
pytest
pyarrow
```

Instalação:

```powershell
pip install MetaTrader5 pandas numpy python-dotenv matplotlib pytest pyarrow
```

---

# 12. Responsabilidade das Dependências

## MetaTrader5

Utilizado para comunicação entre Python e MetaTrader 5.

Responsável por operações como:

```text
conectar ao terminal
consultar conta
consultar símbolos
consultar ticks
consultar candles
obter histórico
```

A versão validada no ambiente atual é:

```text
MetaTrader5 5.0.6090
```

---

## pandas

Utilizado para:

```text
DataFrames
transformação de séries temporais
normalização de timestamps
resample
validação de datasets
Parquet
análises
```

---

## NumPy

Utilizado como dependência numérica e será utilizado futuramente para:

```text
operações vetorizadas
indicadores
estatística
backtesting
análise quantitativa
```

---

## python-dotenv

Utilizado para carregar configurações locais armazenadas em:

```text
.env
```

Principalmente configurações que não devem ficar codificadas diretamente no código.

---

## matplotlib

Utilizado futuramente para visualização de:

```text
equity curves
drawdowns
distribuição de retornos
trades
resultados de backtests
```

---

## pytest

Framework oficial de testes automatizados do projeto.

Estado atual:

```text
25 testes
25 passed
```

---

## pyarrow

Utilizado como engine para leitura e escrita de arquivos:

```text
Parquet
```

É necessário para os datasets históricos atuais.

---

# 13. requirements.txt

Após instalar as dependências:

```powershell
pip freeze > requirements.txt
```

Isso registra as versões presentes no ambiente.

O arquivo permite recriar aproximadamente o mesmo conjunto de dependências em outra máquina.

Instalação futura:

```powershell
pip install -r requirements.txt
```

---

# 14. Estratégia Futura de Dependências

O projeto atualmente utiliza:

```text
requirements.txt
```

gerado através de `pip freeze`.

No futuro pode ser útil separar:

```text
requirements.txt
```

de:

```text
requirements-lock.txt
```

Exemplo conceitual:

```text
requirements.txt
    ↓
dependências diretas

requirements-lock.txt
    ↓
versões completas e transitivas
```

Essa decisão ainda não foi implementada.

---

# 15. Configuração do VS Code

O VS Code deve utilizar o interpretador Python da `.venv`.

Abra:

```text
Ctrl + Shift + P
```

Procure:

```text
Python: Select Interpreter
```

Selecione:

```text
...\FOREX\.venv\Scripts\python.exe
```

Isso evita erros como:

```text
ModuleNotFoundError: No module named 'MetaTrader5'
```

causados pelo uso acidental do Python global.

---

# 16. Verificar Interpretador no VS Code

Dentro do terminal integrado:

```powershell
python -c "import sys; print(sys.executable)"
```

O resultado deve apontar para:

```text
.venv\Scripts\python.exe
```

Também é possível verificar:

```powershell
python --version
```

---

# 17. Instalar MetaTrader 5

O MetaTrader 5 deve estar instalado no Windows.

O projeto atualmente depende de uma instalação local do terminal.

Após instalar:

```text
MetaTrader 5
```

abra o terminal normalmente.

---

# 18. Conta Utilizada

O desenvolvimento inicial utiliza:

```text
Conta Demo
```

em servidor:

```text
MetaQuotes-Demo
```

Nenhuma conta real é necessária nesta etapa.

O projeto deve permanecer em ambiente Demo durante as fases iniciais de desenvolvimento e validação.

---

# 19. Login no Terminal

O terminal MetaTrader 5 pode permanecer autenticado manualmente.

A integração atual utiliza:

```python
mt5.initialize()
```

sem necessidade de armazenar senha dentro do código.

Isso permite que o Python se conecte à instância local já autenticada.

---

# 20. Credenciais

Credenciais não devem ser compartilhadas no código-fonte.

Não colocar:

```python
LOGIN = ...
PASSWORD = ...
```

em arquivos versionados.

Caso credenciais sejam necessárias futuramente, devem ser carregadas através de:

```text
.env
```

ou outro mecanismo seguro.

---

# 21. Arquivo .env

Arquivo:

```text
.env
```

Configuração inicial:

```env
TRADING_ENABLED=false

MT5_SYMBOL=EURUSD
MT5_TIMEFRAME=M15
```

Nesta fase não é necessário armazenar:

```text
MT5_LOGIN
MT5_PASSWORD
```

porque o terminal já autenticado é utilizado.

---

# 22. TRADING_ENABLED

A configuração:

```env
TRADING_ENABLED=false
```

representa uma barreira lógica importante.

O projeto atual é:

```text
READ ONLY
```

Nenhum módulo de execução de ordens foi implementado.

Mesmo futuramente, essa variável não deverá ser considerada proteção suficiente por si só.

A execução deverá possuir múltiplas barreiras independentes.

---

# 23. .gitignore

O arquivo `.gitignore` deve excluir arquivos locais, ambientes virtuais e datasets que não devem ser versionados.

Configuração recomendada:

```gitignore
.venv/
.env

__pycache__/
*.pyc
*.pyo
*.pyd

.vscode/

logs/
*.log

data/raw/
data/cache/

.pytest_cache/
```

Dependendo da estratégia de versionamento dos datasets, outros diretórios poderão ser adicionados posteriormente.

---

# 24. Dados Processados

Atualmente existem datasets como:

```text
data/processed/EURUSD/H1.parquet
data/processed/EURUSD/H4.parquet
```

A política definitiva de versionamento desses arquivos ainda pode evoluir.

Datasets grandes não devem ser adicionados ao Git sem necessidade.

Uma solução futura poderá utilizar:

```text
Git LFS
DVC
object storage
artifact storage
```

caso a reprodutibilidade exija versionamento formal de datasets.

---

# 25. Inicializar Git

Caso o diretório ainda não seja um repositório:

```powershell
git init
```

Verificar:

```powershell
git status
```

Antes do primeiro commit deve-se confirmar que:

```text
.env
.venv
datasets grandes
```

não estão sendo adicionados acidentalmente.

---

# 26. Verificar MetaTrader5 no Python

Com `.venv` ativa:

```powershell
python -c "import MetaTrader5 as mt5; print(mt5.__version__)"
```

Resultado validado:

```text
5.0.6090
```

---

# 27. Verificar pandas e NumPy

```powershell
python -c "import pandas as pd; import numpy as np; print('pandas:', pd.__version__); print('numpy:', np.__version__)"
```

Esse teste confirma que as principais dependências analíticas estão disponíveis.

---

# 28. Teste Básico de Conexão com MT5

Com o MetaTrader 5 aberto:

```powershell
python -c "import MetaTrader5 as mt5; print('init:', mt5.initialize()); print('error:', mt5.last_error()); mt5.shutdown()"
```

Resultado esperado:

```text
init: True
```

Se retornar:

```text
False
```

utilizar:

```python
mt5.last_error()
```

para diagnóstico.

---

# 29. Verificar Terminal

Teste:

```powershell
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.terminal_info()); mt5.shutdown()"
```

O objeto retornado deve indicar que o terminal está conectado.

---

# 30. Verificar Conta

Teste:

```powershell
python -c "import MetaTrader5 as mt5; mt5.initialize(); a=mt5.account_info(); print(a is not None); mt5.shutdown()"
```

Resultado esperado:

```text
True
```

Não é necessário imprimir login ou outras informações sensíveis durante testes comuns.

---

# 31. Verificar EURUSD

```powershell
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.symbol_info('EURUSD')); mt5.shutdown()"
```

O resultado deve retornar informações do símbolo.

Caso o símbolo não esteja visível, pode ser necessário habilitá-lo no Market Watch.

---

# 32. Verificar Tick Atual

```powershell
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.symbol_info_tick('EURUSD')); mt5.shutdown()"
```

O resultado deve possuir, entre outras informações:

```text
bid
ask
time
```

---

# 33. Teste Inicial do Projeto

O projeto possui scripts usados durante o desenvolvimento.

Exemplo:

```text
test_mt5.py
```

Esse script foi utilizado inicialmente para validar:

```text
conexão
terminal
conta
EURUSD
Bid
Ask
spread
candles
UTC
```

Nenhuma ordem é enviada.

---

# 34. Executar Testes Automatizados

Na raiz:

```powershell
pytest -v
```

Estado atual esperado:

```text
collected 25 items
25 passed
```

Os testes atuais cobrem:

```text
MarketData
HistoricalData
TimeframeBuilder
```

---

# 35. Integration Tests

Alguns testes dependem do MetaTrader 5.

O arquivo:

```text
pytest.ini
```

define:

```ini
[pytest]
markers =
    integration: testes que necessitam do MetaTrader 5 conectado
```

Testes desse tipo podem exigir:

```text
MetaTrader 5 aberto
terminal conectado
símbolo disponível
```

---

# 36. Executar Apenas Integration Tests

Quando os testes estiverem marcados:

```powershell
pytest -v -m integration
```

Isso permite separar testes dependentes do terminal de testes puramente locais.

---

# 37. Ambiente de Dados

O dataset atual está localizado em:

```text
data/raw/EURUSD/M15.parquet
```

Para que todos os testes históricos funcionem, esse arquivo precisa estar disponível localmente.

Também existem:

```text
data/processed/EURUSD/H1.parquet
data/processed/EURUSD/H4.parquet
```

---

# 38. Recriar Histórico

Caso o dataset M15 não exista, ele pode ser recriado através de:

```powershell
python collect_history.py
```

O script solicita atualmente histórico de:

```text
EURUSD
M15
```

utilizando coleta em blocos.

---

# 39. Coleta em Chunks

A coleta histórica é realizada em:

```text
90 dias por requisição
```

Isso foi adotado após requisições muito grandes apresentarem comportamento inadequado no terminal.

Fluxo:

```text
2015-01-01
    ↓
90 dias
    ↓
90 dias
    ↓
...
    ↓
data atual
```

Depois os blocos são unidos.

---

# 40. Max Bars in Chart

Durante a preparação do histórico foi verificada a configuração:

```text
Max bars in chart
```

do MetaTrader 5.

No ambiente atual:

```text
100000000
```

Um valor pequeno pode limitar a quantidade de histórico acessível através do terminal.

A configuração pode ser localizada em:

```text
MetaTrader 5
    ↓
Ferramentas
    ↓
Opções
    ↓
Gráficos
```

Após alterar esse valor pode ser necessário reiniciar o terminal.

---

# 41. Histórico Atual

Após carregar o histórico completo disponível, o projeto obteve:

```text
EURUSD M15
288223 candles
```

Período:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:45 UTC
```

---

# 42. Gerar Metadata

Após a coleta:

```powershell
python generate_metadata.py
```

Arquivo gerado:

```text
data/metadata/EURUSD_M15.json
```

A metadata registra características do dataset utilizado no projeto.

---

# 43. Analisar Qualidade

Execute:

```powershell
python analyze_history.py
```

O script verifica propriedades como:

```text
quantidade de candles
primeiro timestamp
último timestamp
duplicados
nulls
OHLC inválido
candles por ano
gaps
spread
tick volume
real volume
```

---

# 44. Construir H1 e H4

Após existir o M15:

```powershell
python build_timeframes.py
```

Arquivos gerados:

```text
data/processed/EURUSD/H1.parquet
data/processed/EURUSD/H4.parquet
```

---

# 45. Resultado H1

Estado validado:

```text
Candles:       72080
Completos:     72018
Incompletos:      62
```

Período:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:00 UTC
```

---

# 46. Resultado H4

Estado validado:

```text
Candles:       18046
Completos:     17929
Incompletos:     117
```

Período:

```text
2015-01-02 08:00 UTC
→
2026-08-07 20:00 UTC
```

---

# 47. Ordem Recomendada para Preparar o Projeto

Após clonar ou copiar o projeto para uma máquina nova:

```text
1. Instalar Python

2. Instalar Git

3. Instalar MetaTrader 5

4. Criar .venv

5. Ativar .venv

6. Instalar requirements.txt

7. Configurar .env

8. Abrir MetaTrader 5

9. Entrar em conta Demo

10. Selecionar interpretador no VS Code

11. Validar conexão MT5

12. Disponibilizar ou coletar dataset M15

13. Gerar H1/H4

14. Executar pytest
```

---

# 48. Exemplo de Setup Completo

PowerShell:

```powershell
git clone <repository>
cd FOREX

python -m venv .venv

.venv\Scripts\activate

python -m pip install --upgrade pip

pip install -r requirements.txt

pytest -v
```

Caso os datasets ainda não existam:

```powershell
python collect_history.py
python generate_metadata.py
python analyze_history.py
python build_timeframes.py
pytest -v
```

---

# 49. Problema: MetaTrader5 não encontrado

Erro:

```text
ModuleNotFoundError:
No module named 'MetaTrader5'
```

Primeiro verificar:

```powershell
python -c "import sys; print(sys.executable)"
```

Se o caminho não apontar para:

```text
.venv\Scripts\python.exe
```

ativar:

```powershell
.venv\Scripts\activate
```

ou selecionar corretamente o interpretador no VS Code.

---

# 50. Problema: initialize() falha

Caso:

```python
mt5.initialize()
```

retorne:

```text
False
```

verificar:

```python
mt5.last_error()
```

Também conferir:

```text
MetaTrader 5 instalado
MetaTrader 5 aberto
terminal funcionando
conta conectada
```

Se a autodetecção do terminal falhar, futuramente pode ser utilizado o caminho explícito do executável.

Isso não foi necessário no ambiente atual.

---

# 51. Problema: Histórico Incompleto

Caso o terminal retorne pouco histórico:

Verificar:

```text
Max bars in chart
```

e aumentar o limite.

Depois:

```text
reiniciar terminal
abrir EURUSD
permitir carregamento do histórico
```

e executar novamente:

```powershell
python collect_history.py
```

---

# 52. Problema: copy_rates_range Invalid Params

Durante o desenvolvimento foi observado:

```text
(-2, 'Terminal: Invalid params')
```

em algumas requisições históricas extensas.

A solução adotada foi:

```text
datas UTC
        ↓
timestamp Unix inteiro
        ↓
coleta em chunks
```

O `MT5Client.rates_range()` converte as datas para timestamps Unix antes da chamada ao MetaTrader.

---

# 53. Timezone

Toda data utilizada pelo projeto deve ser:

```text
timezone-aware
UTC
```

Exemplo:

```python
from datetime import datetime, timezone

date_from = datetime(
    2020,
    1,
    1,
    tzinfo=timezone.utc,
)
```

Evitar:

```python
datetime(2020, 1, 1)
```

quando o timestamp representar mercado.

Esse segundo exemplo é timezone-naive.

---

# 54. Datas Atuais

Quando necessário:

```python
datetime.now(
    timezone.utc
)
```

Preferencialmente remover precisão desnecessária quando apropriado:

```python
datetime.now(
    timezone.utc
).replace(
    microsecond=0
)
```

---

# 55. Ambiente de Produção

Não existe ambiente de produção nesta versão.

Os ambientes atuais podem ser considerados:

```text
Development
Research
Demo Broker Integration
```

Não existe:

```text
Live Trading Environment
```

---

# 56. Segurança do Ambiente

Nunca versionar:

```text
passwords
tokens
broker credentials
private keys
.env
```

Também evitar registrar credenciais em:

```text
logs
screenshots
exceptions
test outputs
```

---

# 57. Estado Esperado Após Setup

Após concluir o setup corretamente:

```text
Python                OK
Virtualenv            OK
MetaTrader5 package   OK
MT5 terminal          OK
Demo account          OK
EURUSD                OK
Historical dataset    OK
Processed datasets    OK
pytest                25/25
```

---

# 58. Checklist

Antes de iniciar desenvolvimento:

```text
[ ] Python funciona

[ ] .venv está criada

[ ] .venv está ativa

[ ] requirements instalados

[ ] VS Code aponta para .venv

[ ] MetaTrader 5 está instalado

[ ] MetaTrader 5 está aberto

[ ] Conta Demo está conectada

[ ] EURUSD está disponível

[ ] mt5.initialize() retorna True

[ ] dataset M15 existe

[ ] datasets H1/H4 existem

[ ] pytest retorna todos os testes verdes

[ ] TRADING_ENABLED=false
```

---

# 59. Versão do Ambiente

Ambiente registrado no marco:

```text
FOREX v0.1
```

Configuração validada:

```text
Windows
Python 3.14.5
MetaTrader5 5.0.6090
pytest 9.1.1
```

Estado dos testes:

```text
25 passed
```

---

# 60. Próximo Documento

O próximo documento é:

```text
docs/04_MT5_INTEGRATION.md
```

Ele documentará em detalhes:

```text
MT5Client
initialize
shutdown
account_info
symbol_info
symbol_info_tick
copy_rates_from_pos
copy_rates_range
bar 0 / bar 1
Bid / Ask
Point / Pip
UTC
histórico
limitações observadas
```