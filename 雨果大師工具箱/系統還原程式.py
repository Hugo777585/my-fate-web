import os
import shutil
import datetime

def list_backups(root_dir):
    """列出根目錄下所有可能的備份資料夾"""
    backups = []
    for d in os.listdir(root_dir):
        full_path = os.path.join(root_dir, d)
        if os.path.isdir(full_path):
            if d.startswith('backup_') or '備份' in d or '雨果系統備份' in d:
                # 排除工具箱本身
                if "工具箱" not in d:
                    backups.append(d)
    
    # 按修改時間排序，最新的在前面
    backups.sort(key=lambda x: os.path.getmtime(os.path.join(root_dir, x)), reverse=True)
    return backups

def restore_backup(backup_path, target_root):
    """將備份資料夾的內容還原到目標根目錄"""
    print(f"🔄 正在從 {os.path.basename(backup_path)} 還原...")
    
    for item in os.listdir(backup_path):
        source = os.path.join(backup_path, item)
        destination = os.path.join(target_root, item)
        
        try:
            if os.path.isdir(source):
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
                print(f"✅ 已還原目錄: {item}")
            else:
                shutil.copy2(source, destination)
                print(f"✅ 已還原檔案: {item}")
        except Exception as e:
            print(f"⚠️ 還原 {item} 時發生錯誤: {e}")

    print("\n✨ 還原作業順利完成！")

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    os.chdir(root_dir)
    
    print("="*40)
    print("⏪ 雨果天命智庫 - 系統還原中心")
    print("="*40)
    
    backups = list_backups('.')
    
    if not backups:
        print("❌ 找不到任何有效的備份檔案。")
        return

    print("\n📦 偵測到以下備份版本 (由新到舊)：")
    for i, b in enumerate(backups):
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(b)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{i+1}] {b} (備份日期: {mtime})")

    choice = input("\n請輸入欲還原的編號 (按 Enter 直接還原最新版 [1]): ").strip()
    
    if choice == "":
        idx = 0
    else:
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(backups):
                print("❌ 編號超出範圍。")
                return
        except ValueError:
            print("❌ 請輸入正確的數字編號。")
            return

    target_backup = backups[idx]
    print(f"\n⚠️  注意：還原將會『覆蓋』目前目錄下的所有同名檔案！")
    confirm = input(f"❓ 您確定要將系統恢復至 {target_backup} 版本嗎？(y/n): ").lower()
    
    if confirm == 'y':
        restore_backup(target_backup, '.')
    else:
        print("🚫 已取消還原，目前系統未做任何變更。")

if __name__ == "__main__":
    main()
