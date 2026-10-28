@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title SUBIR PROYECTO A GITHUB - FONOCENTER IPS

:: Si Python está disponible, delegar a subir_a_github.py que gestiona pegados sin errores
where python >nul 2>nul
if %errorlevel% equ 0 (
    python "%~dp0subir_a_github.py"
    exit /b %errorlevel%
)

echo ======================================================================
echo           CONEXION Y SUBIDA DEL PROYECTO A GITHUB
echo ======================================================================
echo.

:: 1. Localizar Git ejecutable
set "GIT_CMD=git"
where git >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe" (
        set "GIT_CMD=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"
    ) else if exist "C:\Program Files\Git\cmd\git.exe" (
        set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
    ) else (
        echo [ERROR] No se encontro Git instalado en el equipo.
        pause
        exit /b 1
    )
)

echo Git detectado: "!GIT_CMD!"
echo.
set "REPO_URL="
set /p "REPO_URL=Pegue la URL completa del repositorio de GitHub: "

:: Limpiar comillas accidentales
if defined REPO_URL (
    set "REPO_URL=!REPO_URL:"=!"
    set "REPO_URL=!REPO_URL:'=!"
)

if "!REPO_URL!"=="" (
    echo.
    echo [ERROR] No ingreso ninguna URL. Operacion cancelada.
    echo.
    pause
    exit /b 1
)

echo.
echo [1/3] Configurando origen remoto...
"!GIT_CMD!" remote remove origin 2>nul
"!GIT_CMD!" remote add origin "!REPO_URL!"

echo [2/3] Asegurando rama principal 'main'...
"!GIT_CMD!" branch -M main

echo [3/3] Subiendo proyecto a GitHub...
"!GIT_CMD!" push -u origin main

if !errorlevel! equ 0 (
    echo.
    echo ======================================================================
    echo           ¡PROYECTO SUBIDO CON EXITO A GITHUB!
    echo ======================================================================
) else (
    echo.
    echo ======================================================================
    echo [AVISO] Si GitHub solicita autenticacion:
    echo Inicie sesion con su usuario y Personal Access Token (PAT).
    echo ======================================================================
)

echo.
pause
