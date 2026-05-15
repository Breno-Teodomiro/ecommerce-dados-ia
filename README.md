# Imersão Claude Code — Jornada de Dados

> **Dois projetos de IA aplicada a dados de e-commerce**, construídos ao vivo na Imersão Claude Code da [Jornada de Dados](https://suajornadadedados.com.br/).

## 📦 O que tem aqui

| Projeto | Stack | Descrição |
|---------|-------|-----------|
| `case-01-dashboard/` | Streamlit + DuckDB + Plotly | Dashboard analítico com 3 visões para diretores |
| `case-02-agente-telegram/` | Gemini API + Telegram Bot + DuckDB | Agente de dados que responde perguntas e envia relatórios |

---

## 🏗️ Arquitetura

```
arquivos_parquet/          ← Dados brutos (vendas, clientes, produtos, preços)
        │
        ▼
    DuckDB (embutido)      ← Calcula as 3 views gold localmente
        │
        ├── case-01-dashboard/     ← Streamlit lê as views e exibe os gráficos
        │
        └── case-02-agente-telegram/
                ├── agente.py      ← Gemini API + function calling SQL
                └── bot.py         ← Bot Telegram responde perguntas
```

### Views Gold (calculadas na hora pelo DuckDB)

| View | Descrição |
|------|-----------|
| `public_gold_sales.vendas_temporais` | Vendas com dimensões de tempo (data, hora, dia da semana, canal) |
| `public_gold_cs.clientes_segmentacao` | Clientes segmentados: VIP / TOP_TIER / REGULAR |
| `public_gold_pricing.precos_competitividade` | Produtos classificados vs. concorrência |

---

## 🚀 Case 01 — Dashboard Streamlit

### Quickstart local

```bash
cd case-01-dashboard
pip install -r requirements.txt
streamlit run app.py
# Abre em http://localhost:8501
```

### Páginas

| Página | Diretor | Conteúdo |
|--------|---------|----------|
| 🛒 **Vendas** | Comercial | Receita diária · por dia da semana · por hora · por canal · top categorias |
| 👥 **Clientes** | Customer Success | Segmentação VIP · Top 10 clientes · distribuição por estado · tabela filtrável |
| 💰 **Pricing** | Pricing | Posicionamento vs. concorrentes · competitividade por categoria · scatter · alertas |

### Deploy no Streamlit Cloud (gratuito)

1. Fork este repositório no GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Selecione o repositório → `case-01-dashboard/app.py`
4. Em **Secrets**, adicione (se usar Supabase):
   ```toml
   POSTGRES_URL = "postgresql://..."
   ```
5. Clique em **Deploy** ✅

---

## 🤖 Case 02 — Agente Telegram

### Configurar credenciais

```bash
cd case-02-agente-telegram
cp .env.example .env
```

Editar o `.env`:

```env
TELEGRAM=token-do-botfather          # @BotFather no Telegram
GEMINI_API_KEY=AIzaSy...             # aistudio.google.com → Get API key (GRATUITO)
CHAT_ID=                             # preenchido automaticamente pelo bot
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Modo standalone — relatório diário

```bash
python agente.py
# Gera relatório_YYYY-MM-DD.md + envia para o Telegram (se CHAT_ID configurado)
```

### Modo interativo — bot Telegram

```bash
python bot.py
```

No Telegram, abrir `@ProjetoVdaBot` e enviar:

| Comando / Mensagem | O que faz |
|--------------------|-----------|
| `/start` | Boas-vindas + registra CHAT_ID automaticamente |
| `/relatorio` | Gera e envia relatório executivo completo |
| *qualquer texto* | Responde com dados reais via Gemini + SQL |

**Exemplos de perguntas:**
- *"Qual foi a receita desta semana?"*
- *"Quem são os clientes VIP?"*
- *"Quais produtos estão mais caros que os concorrentes?"*
- *"Qual o melhor dia da semana para vendas?"*

### Agendamento automático — Windows Task Scheduler

```bat
schtasks /create /tn "Relatorio Diario" /tr "C:\caminho\case-02-agente-telegram\agendar_relatorio.bat" /sc DAILY /st 08:00
```

Ou use o `agendar_relatorio.bat` diretamente para criar a tarefa no agendador.

### Deploy bot 24/7 — Railway (gratuito com $5/mês de crédito)

1. Acesse [railway.app](https://railway.app) → **New Project → Deploy from GitHub**
2. Selecione este repositório e a pasta `case-02-agente-telegram/`
3. Em **Variables**, adicione:
   ```
   TELEGRAM=seu-token
   GEMINI_API_KEY=sua-chave
   CHAT_ID=seu-chat-id
   ```
4. Railway detecta o `Procfile` e executa `python bot.py` automaticamente ✅

---

## 🗄️ (Opcional) Migrar para Supabase

Por padrão, os projetos usam **DuckDB local** (zero configuração).
Para usar PostgreSQL real no Supabase:

### 1. Criar as tabelas no Supabase

```bash
# No SQL Editor do Supabase, execute:
supabase/setup.sql
```

### 2. Carregar os dados

```bash
# Adicionar POSTGRES_URL no .env e rodar:
python supabase/load_data.py
```

### 3. Configurar os apps

Adicionar no `.env` dos dois projetos:
```env
POSTGRES_URL=postgresql://postgres.XXX:senha@host:6543/postgres
```

Os `db.py` detectam automaticamente e usam PostgreSQL em vez de DuckDB.

---

## 📁 Estrutura do Projeto

```
├── arquivos_parquet/
│   ├── vendas.parquet
│   ├── clientes.parquet
│   ├── produtos.parquet
│   └── preco_competidores.parquet
│
├── case-01-dashboard/
│   ├── app.py                  # App Streamlit (3 páginas)
│   ├── db.py                   # DuckDB + views gold
│   ├── requirements.txt
│   └── .env.example
│
├── case-02-agente-telegram/
│   ├── agente.py               # Gemini API + relatório + envio Telegram
│   ├── bot.py                  # Bot Telegram assíncrono
│   ├── db.py                   # DuckDB + views gold + validação SQL
│   ├── .llm/database.md        # Catálogo de dados para o LLM
│   ├── Procfile                # Deploy Railway
│   ├── railway.toml            # Config Railway
│   ├── agendar_relatorio.bat   # Windows Task Scheduler
│   ├── requirements.txt
│   └── .env.example
│
├── supabase/
│   ├── setup.sql               # DDL das tabelas gold
│   └── load_data.py            # Script de carga Parquet → Supabase
│
├── prd-agente-relatorios.md    # PRD do agente
├── prd-dashboard.md            # PRD do dashboard
├── .gitignore
└── README.md
```

---

## 🛠️ Stack Tecnológico

| Camada | Tecnologia |
|--------|-----------|
| **Dados** | DuckDB (local) · Supabase/PostgreSQL (produção) |
| **LLM** | Google Gemini 2.0 Flash (gratuito via AI Studio) |
| **Dashboard** | Streamlit · Plotly |
| **Bot** | python-telegram-bot v20+ |
| **Linguagem** | Python 3.10+ |

---

## 📄 Licença

MIT — livre para usar, modificar e distribuir.
