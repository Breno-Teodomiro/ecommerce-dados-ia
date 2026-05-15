# 📊 E-Commerce Analytics Ecosystem (Dual-Mode Data Architecture)

Um ecossistema completo de dados com Inteligência Artificial, construído para resolver a latência de decisão e unificar indicadores de Vendas, Customer Success e Pricing em um varejo digital.

---

## 🎯 O Desafio de Negócio

Em muitos e-commerces, os gestores sofrem com:
1. **Silos de Dados:** Informações espalhadas em planilhas pesadas, ERPs lentos e plataformas terceiras.
2. **Dependência Técnica:** Diretores precisando abrir chamados de TI/Dados apenas para responder perguntas simples como *"Qual foi a categoria mais rentável ontem?"*.
3. **Alto Custo Estrutural:** Manter data warehouses robustos e licenças de BI (PowerBI, Tableau) consome uma fatia imensa do orçamento de tecnologia.

## 💡 A Solução e Arquitetura

Construímos um ecossistema com **Custo Zero** (100% Free Tier) focado em performance e autonomia:

1. **Pipeline Local de Transformação (ETL/ELT):** Lemos os dados brutos massivos em formato Parquet usando o **DuckDB** local. Isso garante processamento ultrarrápido das regras de negócios (Gold Layer) sem gastar processamento em nuvem.
2. **Cloud Database Serverless:** As visões analíticas mastigadas (Gold Views) são injetadas automaticamente no **Supabase (PostgreSQL)**, criando uma fonte de verdade (Single Source of Truth) na nuvem.
3. **Acesso C-Level via Dashboard:** Uma aplicação web elegante desenvolvida em **Streamlit**, hospedada gratuitamente no Streamlit Cloud, fornecendo indicadores acionáveis em 3 verticais: Comercial, Customer Success e Pricing.
4. **Autonomia com Agente Autônomo IA:** Um bot no **Telegram** integrado à IA do **Groq (Llama 3.3)** capaz de converter a linguagem natural do diretor em consultas SQL e enviar resumos gerenciais formatados.

---

## 🛠️ Tecnologias Utilizadas e Custos

Esta arquitetura foi desenhada propositalmente para provar que é possível ter dados maduros com ferramentas modernas de custo extremamente baixo:

- **DuckDB:** Processamento OLAP local das transformações (Custo: **$0**)
- **Supabase (PostgreSQL):** Banco de dados relacional em nuvem com Transaction Pooler (Custo: **$0** / Free Tier)
- **Streamlit + Plotly:** Construção e hospedagem do App Web analítico (Custo: **$0** / Community Cloud)
- **Groq (Llama 3.3 70B):** Inteligência artificial ultrarrápida (Tool Calling/SQL) para conversação (Custo: **$0** / Free Tier)
- **Railway:** Hospedagem em contêiner Docker para o Agente Telegram funcionar 24/7 (Custo: **$0** / Plano Mensal Gratuito)
- **Python:** Orquestração de todo o pipeline e APIs (Custo: **$0**)

---

## 🚀 Como Executar o Projeto

O sistema inteiro suporta operação "Dual-Mode" (local ou em nuvem). Para testar:

### 1. Preparar o Ambiente
Crie as variáveis de ambiente `.env` baseando-se no arquivo `.env.example`.
- Para rodar via Supabase Cloud, preencha a `POSTGRES_URL` (recomendado porta 6543).
- Para rodar via DuckDB local, basta deixar a URL em branco.

### 2. Rodar o Dashboard (Streamlit)
```bash
cd case-01-dashboard
pip install -r requirements.txt
streamlit run app.py
```

### 3. Rodar o Agente Telegram
```bash
cd case-02-agente-telegram
pip install -r requirements.txt
python bot.py
```
*(No Telegram, inicie a conversa com `/start` para interagir com os dados do banco e `/relatorio` para forçar a geração de um overview diário).*

---

### Estrutura do Repositório
- `/arquivos_parquet`: Base de dados transacional bruta simulada.
- `/supabase`: Scripts `.sql` de provisionamento do banco e `.py` para carga e persistência das views gold.
- `/case-01-dashboard`: Aplicação visual e queries analíticas (Streamlit).
- `/case-02-agente-telegram`: Orquestrador LLM e integração com a API do Telegram.
