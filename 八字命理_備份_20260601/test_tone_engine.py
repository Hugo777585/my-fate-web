
from tone_engine import analyze_tone_strategy, engine, ToneStrategy

def test_basic_logic():
    print("--- 執行基礎邏輯測試 ---")
    # 測試案例一：遇到惡意代碼 (Guard 模式)
    test_input_1 = "他昨天對我飆髒話說他媽的，還說我傷他，截圖明明就抓到他跟別人曖昧，現在還擺高姿態要我明天帶筆電去給他。" 
    bazi_info_1 = ["劫財", "七殺"] 
    result_1 = analyze_tone_strategy(test_input_1, bazi_info_1) 
    
    print(f"啟動模式: {result_1['mode']}") 
    assert "Guard" in result_1['mode']
    assert "劫財" in result_1['system_prompt']
    
    # 測試案例二：遇到情緒低谷 (Healer 模式)
    test_input_2 = "我昨天忍不住罵了他很難聽的話，現在覺得心裡很痛，一直睡不著。我付出了很多，不知道是不是我做錯了，真的好猶豫怎麼辦。" 
    result_2 = analyze_tone_strategy(test_input_2) 
    
    print(f"啟動模式: {result_2['mode']}") 
    assert "Healer" in result_2['mode']

    # 測試案例三：中立模式
    test_input_3 = "我想問問今年的財運如何？"
    result_3 = analyze_tone_strategy(test_input_3)
    print(f"啟動模式: {result_3['mode']}")
    assert "Neutral" in result_3['mode']
    print("✅ 基礎邏輯測試通過！\n")

def test_extensibility():
    print("--- 執行擴充性測試 ---")
    # 測試動態註冊新策略
    new_strategy = ToneStrategy(
        mode="Success (事業衝刺模式)",
        keywords=["創業", "升職", "加薪", "大賺"],
        system_prompt="系統判定用戶目前事業運極佳。請切換為『激勵、振奮、專業』的語氣。鼓勵用戶大膽前行，把握當前機會。",
        action_advice="火力全開：現在是進攻的最佳時機，不要猶豫。",
        priority=15 # 高優先權
    )
    engine.register_strategy(new_strategy)

    test_input_4 = "我最近想創業，感覺會大賺一筆！"
    result_4 = analyze_tone_strategy(test_input_4)
    print(f"啟動模式: {result_4['mode']}")
    assert "Success" in result_4['mode']
    print("✅ 擴充性測試通過！\n")

if __name__ == "__main__":
    test_basic_logic()
    test_extensibility()
    print("🚀 所有測試圓滿達成！")
