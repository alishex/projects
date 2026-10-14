@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js 24 ni https://nodejs.org dan o'rnating.
  pause
  exit /b 1
)
echo INTIM SHOP - http://localhost:3000
node server.mjs
pause
