@echo off
cd /d "%~dp0"
echo Iniciando TutorIA...
echo Recuerde tener LM Studio abierto con el servidor encendido.
start "" http://127.0.0.1:5000
python app.py
pause
