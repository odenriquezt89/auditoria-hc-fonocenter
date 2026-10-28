@echo off
chcp 65001 > nul
title SUBIR PROYECTO A GITHUB - FONOCENTER IPS
echo ======================================================================
echo           CONEXIÓN Y SUBIDA DEL PROYECTO A GITHUB
echo ======================================================================
echo.
set /p REPO_URL="Pegue aquí la URL de su repositorio de GitHub (ej: https://github.com/usuario/auditoria-fonocenter.git): "

if "%REPO_URL%"=="" (
    echo [ERROR] No ha ingresado ninguna URL. Operación cancelada.
    pause
    exit /b
)

echo.
echo [1/3] Vinculando repositorio remoto origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo [2/3] Asegurando rama principal 'main'...
git branch -M main

echo [3/3] Subiendo cambios a GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo ¡PROYECTO SUBIDO CON ÉXITO A GITHUB!
    echo ======================================================================
) else (
    echo.
    echo [AVISO] Si es la primera vez que se conecta a GitHub, asegúrese de haber iniciado sesión
    echo o de haber configurado sus credenciales de GitHub / Personal Access Token.
)

echo.
pause
