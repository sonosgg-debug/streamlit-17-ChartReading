@echo off
title Technical Analysis Pro - Chart Reading Dashboard
echo ========================================================
echo   Technical Analysis Pro Dashboard Launcher
echo ========================================================
echo.
echo Starting Streamlit server...
echo The dashboard will automatically open in your web browser.
echo Press Ctrl + C to stop the server.
echo.
python -m streamlit run app.py
pause
