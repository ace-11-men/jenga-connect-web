@echo off
REM Jenga Connect Windows Build Script
REM Run this on Windows 10/11 with Python installed

echo Installing dependencies...
pip install Django==6.0.3 djangorestframework==3.14.0 django-cors-headers==4.3.1 python-decouple==3.8 python-dotenv==1.0.0 psycopg2-binary==2.9.9 pyinstaller

echo.
echo Building Windows executable...
pyinstaller --name "JengaConnect" --onefile --console --add-data "core\templates;core\templates" --add-data "core\static;core\static" --hidden-import=django --hidden-import=django.core --hidden-import=django.core.management --hidden-import=rest_framework --hidden-import=corsheaders --hidden-import=decouple --hidden-import=dotenv --hidden-import=psycopg2 main.py

echo.
echo Build complete!
echo Your executable is in the dist folder: dist\JengaConnect.exe
pause
