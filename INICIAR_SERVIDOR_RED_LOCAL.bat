@echo off
title FONOCENTER IPS - Servidor de Auditoria Clinica Multiusuario
color 0A
chcp 65001 >nul
cls
echo ==============================================================================
echo       FONOCENTER IPS - SISTEMA DE AUDITORIA CLINICA Y CONTROL RBAC
echo               INICIANDO SERVIDOR DE RED LOCAL (LAN / WI-FI)
echo ==============================================================================
echo.
python server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ocurrió un inconveniente al iniciar el servidor con Python.
    echo Verifique que Python 3.10+ esté instalado y en la variable PATH del sistema.
    pause
)
