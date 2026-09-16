@echo off
:: Backward-compatible entry point kept because older docs/changelogs referenced setup.bat.
call "%~dp0install.bat"
exit /b %errorlevel%
