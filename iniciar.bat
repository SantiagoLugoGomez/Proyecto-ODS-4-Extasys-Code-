@echo off
rem Inicia TutorIA en Windows. La primera vez crea un entorno virtual e instala
rem las dependencias; requiere Internet solo esa vez.
setlocal
cd /d "%~dp0"
title TutorIA

where python >nul 2>nul
if errorlevel 1 goto sin_python

if exist ".venv\instalado.txt" goto iniciar

echo Preparando TutorIA por primera vez...
python -m venv .venv
if errorlevel 1 goto error_instalacion
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto error_instalacion
echo listo> ".venv\instalado.txt"

:iniciar
echo Recuerde tener LM Studio abierto con el servidor local encendido en el puerto 1234.
echo Para cerrar TutorIA cierre esta ventana.
set "TUTORIA_ABRIR_NAVEGADOR=1"
".venv\Scripts\python.exe" app.py
pause
exit /b 0

:sin_python
echo No se encontro Python. Instale Python 3.10 o superior desde https://www.python.org/downloads/
echo y marque la opcion "Add python.exe to PATH" durante la instalacion.
pause
exit /b 1

:error_instalacion
echo No se pudieron instalar las dependencias. Revise la conexion a Internet e intente de nuevo.
pause
exit /b 1
