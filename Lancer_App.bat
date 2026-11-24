@echo off
title Energy Management System
cd /d "%~dp0"
echo Lancement de l application... (ne ferme pas cette fenetre)
python -m streamlit run app.py --theme.base dark --theme.primaryColor "#3dffb0" --theme.backgroundColor "#070b14" --theme.secondaryBackgroundColor "#0d1424" --theme.textColor "#ffffff"
pause
