@echo off
setlocal
set "DIR=%~dp0.."
set "PY="
if exist "%DIR%\.venv\Scripts\python.exe" (
  set "PY=%DIR%\.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo web-reach-ensure: no Python found on PATH 1>&2
  exit /b 1
)
pushd "%DIR%"
%PY% -m gpu_agent.web_reach_ensure %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
