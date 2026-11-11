@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Teste: converte somente o menor arquivo, sem precisar digitar caminho.
set "ARQUIVO=%~dp01SKE806420S0001-SL060420C.step"

if not exist "%ARQUIVO%" (
    echo Arquivo nao encontrado: %ARQUIVO%
    echo Coloque este .bat na mesma pasta dos .step.
    pause
    exit /b 1
)

call "%~dp0converter_step.bat" "%ARQUIVO%"
