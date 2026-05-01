@echo off
:: ================================================
::  Guandan Launcher
::  Double-click this file to open game.html
::  Put this .bat file in the same folder as game.html
:: ================================================

set "FILE=%~dp0game.html"

if not exist "%FILE%" (
    echo ERROR: game.html not found in this folder.
    echo Make sure play.bat and game.html are in the same directory.
    pause
    exit /b 1
)

echo Opening game.html...
start "" "%FILE%"