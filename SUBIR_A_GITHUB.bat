@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title SUBIR AUDITORIA HC FONOCENTER A GITHUB

echo ======================================================================
echo           SUBIENDO AUDITORIA HC FONOCENTER A GITHUB
echo ======================================================================
echo.
echo Repositorio Vinculado:
echo https://github.com/odenriquezt89/auditoria-hc-fonocenter.git
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
    )
)

:: Asegurar helper de credenciales de Windows
"!GIT_CMD!" config --global credential.helper wincred 2>nul
"!GIT_CMD!" branch -M main 2>nul
"!GIT_CMD!" remote set-url origin "https://github.com/odenriquezt89/auditoria-hc-fonocenter.git" 2>nul

echo [1/2] Verificando rama principal 'main'...
echo [2/2] Transfiriendo archivos a GitHub (git push)...
echo.
echo ----------------------------------------------------------------------
echo NOTA: Si la consola le pide credenciales de GitHub:
echo   - Username: odenriquezt89
echo   - Password: Pegue su Personal Access Token (Token clásico de GitHub)
echo ----------------------------------------------------------------------
echo.

"!GIT_CMD!" push -u origin main

if !errorlevel! equ 0 (
    echo.
    echo ======================================================================
    echo           ¡PROYECTO SUBIDO CON EXITO A GITHUB!
    echo Puede revisarlo en: https://github.com/odenriquezt89/auditoria-hc-fonocenter
    echo ======================================================================
) else (
    echo.
    echo ======================================================================
    echo Hubo un fallo en la autenticacion de GitHub.
    echo Asegurese de usar un Personal Access Token (PAT) con permiso 'repo'.
    echo ======================================================================
)

echo.
pause
