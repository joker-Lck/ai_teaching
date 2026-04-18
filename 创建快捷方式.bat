@echo off
chcp 65001 >nul
echo ========================================
echo    创建桌面快捷方式
echo ========================================
echo.

echo 正在创建桌面快捷方式...
powershell -ExecutionPolicy Bypass -File "%~dp0创建快捷方式.ps1"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo 成功！桌面快捷方式已创建
    echo ========================================
) else (
    echo.
    echo ========================================
    echo 创建失败，请手动创建：
    echo ========================================
    echo 1. 右键桌面 - 新建 - 快捷方式
    echo 2. 输入路径：
    echo    %~dp0启动AI教学助手.bat
    echo 3. 名称：AI教学助手
    echo 4. 点击完成
)

echo.
pause
