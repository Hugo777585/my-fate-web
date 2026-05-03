import os
import shutil
import datetime

def main():
    # 因為程式放在子資料夾，所以根目錄是上一層
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    os.chdir(root_dir)

    print("="*40)
    print("🚀 雨果天命智庫 - 系統自動備份中")
    print("="*40)

    # 建立備份資料夾名稱 (繁體中文 + 時間戳記)
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder_name = f"雨果系統備份_{now_str}"
    
    print(f"📁 建立備份資料夾: {backup_folder_name}")
    os.makedirs(backup_folder_name, exist_ok=True)

    # 定義要排除的資料夾（避免無限備份）
    exclude_list = [
        backup_folder_name, 
        "雨果大師工具箱", 
        "雨果系統還原工具",
        "backup_", 
        "備份", 
        "temp_backup",
        ".git",
        ".devcontainer",
        "__pycache__"
    ]

    count_files = 0
    count_dirs = 0

    # 遍歷根目錄檔案進行備份
    for item in os.listdir('.'):
        # 檢查是否在排除名單內 (關鍵字匹配)
        should_exclude = False
        for ex in exclude_list:
            if ex in item:
                should_exclude = True
                break
        
        if should_exclude:
            continue

        source = item
        destination = os.path.join(backup_folder_name, item)

        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
                print(f"✅ 備份目錄: {item}")
                count_dirs += 1
            else:
                shutil.copy2(source, destination)
                print(f"✅ 備份檔案: {item}")
                count_files += 1
        except Exception as e:
            print(f"⚠️ 備份 {item} 時發生錯誤: {e}")

    print("\n" + "="*40)
    print(f"✨ 備份完成！")
    print(f"📊 統計：共備份 {count_dirs} 個目錄，{count_files} 個檔案")
    print(f"📍 位置：{os.path.join(root_dir, backup_folder_name)}")
    print("="*40)

if __name__ == "__main__":
    main()
