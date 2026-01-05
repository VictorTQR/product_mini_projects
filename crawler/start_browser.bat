@echo off
chcp 65001 >nul
echo ======================================================================
echo Chrome CDP 启动器
echo ======================================================================
echo.

set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
set DEBUG_PORT=9222
set USER_DATA_DIR=%~dp0chrome_profile

echo [配置信息]
echo   Chrome路径: %CHROME_PATH%
echo   调试端口: %DEBUG_PORT%
echo   用户数据: %USER_DATA_DIR%
echo.

if not exist "%CHROME_PATH%" (
    echo [错误] Chrome未找到，请修改CHROME_PATH变量
    pause
    exit /b 1
)

echo [启动Chrome]
echo   请保持此窗口打开，Chrome将在此目录下保存数据
echo.
echo   启动后，可以运行Python脚本连接
echo.
echo ======================================================================
echo.

"%CHROME_PATH%" ^
    --remote-debugging-port=%DEBUG_PORT% ^
    --user-data-dir="%USER_DATA_DIR%" ^
    --start-maximized ^
    --disable-blink-features=AutomationControlled ^
    --exclude-switches=enable-automation ^
    --no-sandbox

echo.
echo [Chrome已关闭]
pause
