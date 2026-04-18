
import os
import subprocess

def create_shortcut():
    # 設定路徑
    target_path = r"G:\AI下載\啟動下載器.bat"
    shortcut_name = "MissAV 下載大師 (Neon).lnk"
    
    # 使用 PowerShell 獲取正確的桌面路徑 (支援 OneDrive 或移動過的路徑)
    powershell_script = f'''
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "{shortcut_name}"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "{target_path}"
    $Shortcut.WorkingDirectory = "G:\\AI下載"
    $Shortcut.Description = "啟動 Cyberpunk 霓虹風格影片下載器"
    $Shortcut.IconLocation = "shell32.dll, 14"
    $Shortcut.Save()
    Write-Host "SUCCESS_PATH:$ShortcutPath"
    '''
    
    try:
        # 執行 PowerShell
        result = subprocess.run(["powershell", "-Command", powershell_script], capture_output=True, text=True, check=True)
        if "SUCCESS_PATH" in result.stdout:
            path = result.stdout.split("SUCCESS_PATH:")[1].strip()
            print(f"✅ 捷徑已成功建立在桌面：{path}")
        else:
            print(f"❌ 建立捷徑失敗：{result.stderr}")
    except Exception as e:
        print(f"❌ 建立捷徑發生錯誤：{e}")

if __name__ == "__main__":
    create_shortcut()
