@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Uso: de duplo clique (converte todos os .step da pasta) ou arraste um .step/pasta sobre este arquivo.

set "VENV=%~dp0.venv_step"
set "PYEXE="

rem CadQuery funciona melhor com Python 3.10 a 3.12
for %%V in (3.12 3.11 3.10 3.13) do if not defined PYEXE (py -%%V -c "import sys" >nul 2>&1 && set "PYEXE=py -%%V")
if not defined PYEXE (python -c "import sys" >nul 2>&1 && set "PYEXE=python")
if not defined PYEXE goto sem_python

if exist "%VENV%\Scripts\python.exe" goto venv_ok
echo Criando ambiente virtual local...
%PYEXE% -m venv "%VENV%"
if errorlevel 1 goto falha

:venv_ok
"%VENV%\Scripts\python.exe" -c "import cadquery" >nul 2>&1
if not errorlevel 1 goto executar
echo Instalando o CadQuery - pode levar alguns minutos...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip -q
"%VENV%\Scripts\python.exe" -m pip install cadquery
if errorlevel 1 goto falha

:executar
set "PYTHONIOENCODING=utf-8"
"%VENV%\Scripts\python.exe" "%~dp0converter_step.py" %*
goto fim

:sem_python
echo Python nao encontrado.
goto fim

:falha
echo Falha ao preparar o ambiente. Copie a mensagem acima e envie ao Claude.

:fim
echo.
pause
