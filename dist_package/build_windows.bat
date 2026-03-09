@echo off
REM Jenga Connect Windows Build Script
REM Run this on Windows 10/11 with Python 3.10+ installed
REM
REM Instructions:
REM 1. Install Python 3.10+ from https://www.python.org/downloads/
REM 2. Open Command Prompt in this folder
REM 3. Run: build_windows.bat
REM 4. The executable will be in the dist folder

echo ========================================
echo Jenga Connect - Windows Build Script
echo ========================================
echo.

echo Step 1: Installing dependencies...
pip install Django==6.0.3 djangorestframework==3.14.0 django-cors-headers==4.3.1 python-decouple==3.8 python-dotenv==1.0.0 psycopg2-binary==2.9.9 pyinstaller

echo.
echo Step 2: Building Windows executable...
pyinstaller --name "JengaConnect" --onefile --console --hidden-import=django --hidden-import=django.core --hidden-import=django.core.management --hidden-import=rest_framework --hidden-import=corsheaders --hidden-import=decouple --hidden-import=dotenv --hidden-import=psycopg2 main.py

echo.
echo ========================================
echo Build complete!
echo ========================================
echo Your executable is at: dist\JengaConnect.exe
echo.
echo To run the app:
echo 1. Copy dist\JengaConnect.exe to your desired location
echo 2. Also copy db.sqlite3 and media folder next to the exe
echo 3. Run JengaConnect.exe
echo 4. Open browser at http://localhost:8000
echo.
pause
