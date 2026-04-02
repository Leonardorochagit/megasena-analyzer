@echo off
cd /d "%~dp0"
echo ========================================
echo   Mega Sena Analyzer - Iniciando...
echo ========================================
echo.
echo Abrindo aplicacao no navegador...
echo URL: http://localhost:8501
echo.
echo Para fechar o aplicativo, pressione Ctrl+C
echo ========================================
echo.

streamlit run megasena_app.py

pause
