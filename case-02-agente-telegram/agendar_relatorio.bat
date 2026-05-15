@echo off
REM agendar_relatorio.bat — Gera relatório diário e envia para o Telegram
REM Configure no Windows Task Scheduler para rodar às 8h todo dia

cd /d "%~dp0"
echo [%date% %time%] Iniciando geração do relatório... >> relatorio.log
python agente.py >> relatorio.log 2>&1
echo [%date% %time%] Concluído. >> relatorio.log
