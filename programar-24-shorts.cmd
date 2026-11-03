@echo off
setlocal
chcp 65001 >nul
title ARQUIVO OTAKU - 24 SHORTS AGENDADOS NO YOUTUBE
if /I "%~1"=="planejar" goto PREVIEW
if /I "%~1"=="agendar" goto SCHEDULE
echo.
echo ARQUIVO OTAKU: 8 episodios + 8 curiosidades + 8 nostalgias
echo.
echo Uso:
echo   programar-24-shorts.cmd planejar 2026-11-05
echo   programar-24-shorts.cmd agendar 2026-11-05
echo.
echo Sem data: inicia as 09:00 (Brasilia), dois dias depois da execucao.
echo Ordem: EP - Curiosidade - Voce lembra, a cada 1 hora.
echo 'agendar' faz upload PRIVADO e configura a liberacao automatica no YouTube.
echo 'planejar' nao gera nem envia videos.
echo.
exit /b 0

:PREVIEW
if "%~2"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0programar-24-shorts.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0programar-24-shorts.ps1" -DataInicio "%~2"
)
exit /b %errorlevel%

:SCHEDULE
if "%~2"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0programar-24-shorts.ps1" -Agendar
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0programar-24-shorts.ps1" -Agendar -DataInicio "%~2"
)
exit /b %errorlevel%
