@echo off
REM Feather Code MCP - Windows Installation Script
REM Supports Windows 10/11 with automatic dependency detection

setlocal enabledelayedexpansion

echo 🚀 Feather Code MCP Installation
echo =================================

REM Check Python installation
echo.
echo 🐍 Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Python not found. Please install Python 3.8 or later from python.org
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
        for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    )
) else (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
)

echo ✅ Python found: %PYTHON_VERSION%

REM Check pip
echo.
echo 📦 Checking pip installation...
%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pip not found. Please install pip.
    pause
    exit /b 1
) else (
    echo ✅ pip found
)

REM Install dependencies
echo.
echo 📚 Installing dependencies...
set REQUIREMENTS=mcp>=1.0.0 PyJWT>=2.8.0 requests>=2.31.0 cryptography>=41.0.0

for %%r in (%REQUIREMENTS%) do (
    echo Installing %%r...
    %PYTHON_CMD% -m pip install "%%r"
    if %errorlevel% neq 0 (
        echo ❌ Failed to install %%r
        pause
        exit /b 1
    ) else (
        echo ✅ Installed %%r
    )
)

REM Setup directory
echo.
echo 📁 Setting up installation directory...
set INSTALL_DIR=%USERPROFILE%\.feather-code
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy files
echo Copying MCP server files...
copy feather_code.py "%INSTALL_DIR%\" >nul
copy requirements.txt "%INSTALL_DIR%\" >nul
if exist ".env.example" copy .env.example "%INSTALL_DIR%\" >nul

echo ✅ Files copied to %INSTALL_DIR%

REM Create wrapper batch file
echo.
echo 🔧 Creating wrapper script...
set WRAPPER_SCRIPT=%INSTALL_DIR%\feather-code.bat

echo @echo off > "%WRAPPER_SCRIPT%"
echo cd /d "%INSTALL_DIR%" >> "%WRAPPER_SCRIPT%"
echo %PYTHON_CMD% feather_code.py %%* >> "%WRAPPER_SCRIPT%"

echo ✅ Wrapper script created at %WRAPPER_SCRIPT%

REM Setup environment file
echo.
echo 🔐 Setting up authentication...
set ENV_FILE=%INSTALL_DIR%\.env
if not exist "%ENV_FILE%" (
    echo Creating environment file...
    set /p github_pat="Enter GitHub Personal Access Token (or press Enter to skip): "
    if defined github_pat (
        echo GITHUB_PAT=!github_pat! > "%ENV_FILE%"
        echo ✅ GitHub PAT saved to %ENV_FILE%
    ) else (
        if exist "%INSTALL_DIR%\.env.example" (
            copy "%INSTALL_DIR%\.env.example" "%ENV_FILE%" >nul
        )
        echo ⚠️ Environment file created. Edit %ENV_FILE% to add your GitHub PAT
    )
) else (
    echo ℹ️ Environment file already exists at %ENV_FILE%
)

REM Add to PATH
echo.
echo 🛣️ Checking PATH...
echo %PATH% | findstr /C:"%INSTALL_DIR%" >nul
if %errorlevel% neq 0 (
    echo ⚠️ %INSTALL_DIR% is not in your PATH
    echo Would you like to add it to your PATH? (y/n)
    set /p add_path=
    if /i "!add_path!"=="y" (
        setx PATH "%PATH%;%INSTALL_DIR%"
        echo ✅ Added to PATH (restart your command prompt)
    ) else (
        echo You can run feather-code using: "%WRAPPER_SCRIPT%"
    )
) else (
    echo ✅ PATH is correctly configured
)

REM Installation complete
echo.
echo 🎉 Installation Complete!
echo ========================
echo ✅ Feather Code MCP is now installed

echo.
echo 📋 Next steps:
echo 1. Set up your GitHub authentication in %ENV_FILE%
echo 2. Test the installation: feather-code.bat
echo 3. Add to Claude Code:
echo    claude mcp add feather-code "%WRAPPER_SCRIPT%"

echo.
echo 🔗 Repository detection:
echo Run from a git repository or set environment variables:
echo set GITHUB_OWNER=your-username
echo set GITHUB_REPO=your-repository

echo.
echo 📚 Documentation:
echo Check the README.md for detailed usage instructions

echo.
echo ✅ Installation successful! 🚀
pause