@echo off
chcp 65001 > nul
title FONOCENTER IPS - SERVIDOR STREAMLIT
echo ======================================================================
echo           INICIANDO APLICACIÓN CON STREAMLIT - FONOCENTER IPS
echo ======================================================================
echo.
echo Abriendo servidor Streamlit en el navegador...
echo Presione Ctrl+C para detener en cualquier momento.
echo.
python -m streamlit run streamlit_app.py
pause
