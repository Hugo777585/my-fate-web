
import re

class ToneStrategy:
    def __init__(self, mode, system_prompt, action_advice, keywords=None, bazi_triggers=None, priority=0):
        self.mode = mode
        self.system_prompt = system_prompt
        self.action_advice = action_advice
        self.keywords = keywords or []
        self.bazi_triggers = bazi_triggers or []
        self.priority = priority

    def calculate_score(self, user_input):
        if not self.keywords:
            return 0
        return sum(1 for word in self.keywords if word in user_input)

class DynamicToneEngine:
    def __init__(self):
        self.strategies = []
        self._setup_default_strategies()

    def _setup_default_strategies(self):
        # 1. 強硬保鑣模式 (Guard) - 高優先權
        self.register_strategy(ToneStrategy(
            mode="Guard (強硬保鑣模式)",
            keywords=[
                "說謊", "騙", "截圖", "交友軟體", "別人聊天", "曖昧", 
                "很兇", "髒話", "他媽的", "聽不懂人話", "冷暴力", "擺高姿態", 
                "不想去想", "以後再說", "錢", "店面", "借款", "勢利", "現實"
            ],
            system_prompt="系統判定用戶正在遭遇高風險關係或惡意消耗。請切換為『強硬、理智、犀利』的語氣。直接點破對方防禦性暴怒與推卸責任的行為，警告用戶立即設立防火牆，停止投入實體資產與情緒成本。",
            action_advice="物理級格式化：立即停損，收回資源，轉身離開。",
            bazi_triggers=["劫財"],
            priority=10
        ))

        # 2. 深夜酒館模式 (Healer)
        self.register_strategy(ToneStrategy(
            mode="Healer (深夜酒館模式)",
            keywords=[
                "好累", "心痛", "捨不得", "睡不著", "一直哭", "很煩", 
                "猶豫", "怎麼辦", "可是", "放不下", "是不是我做錯了", 
                "付出很多", "想照顧", "等他", "門沒關", "不知道該怎麼辦"
            ],
            system_prompt="系統判定用戶目前能量極低，處於受傷與自我懷疑狀態。請切換為『溫暖、包容、同理』的語氣。不要急著叫用戶做決定，告訴用戶『這不是你的錯』，允許他們現在的無力感，並給予情緒上的緩衝空間。",
            action_advice="系統休眠：今晚好好睡一覺，原諒失控的自己，不用急著行動。",
            priority=5
        ))

    def register_strategy(self, strategy):
        self.strategies.append(strategy)
        # 依優先權排序，高優先權在前
        self.strategies.sort(key=lambda x: x.priority, reverse=True)

    def analyze(self, user_input, bazi_info=None):
        """
        分析用戶輸入與八字資訊，決定最佳語氣策略。
        """
        bazi_info = bazi_info or []
        best_strategy = None
        max_score = 0

        # 預設中立策略
        default_result = {
            "mode": "Neutral",
            "system_prompt": "請客觀分析命盤，給出中肯的建議。",
            "action_advice": "冷靜觀察，維持日常運作。"
        }

        for strategy in self.strategies:
            score = strategy.calculate_score(user_input)
            
            # 如果分數大於 0，且比目前最好的分數高（或優先權更高）
            if score > 0:
                if score > max_score or (best_strategy and strategy.priority > best_strategy.priority):
                    best_strategy = strategy
                    max_score = score

        if best_strategy:
            result = {
                "mode": best_strategy.mode,
                "system_prompt": best_strategy.system_prompt,
                "action_advice": best_strategy.action_advice
            }

            # 檢查八字觸發條件
            for trigger in best_strategy.bazi_triggers:
                if trigger in bazi_info:
                    if trigger == "劫財" and "Guard" in best_strategy.mode:
                        result["system_prompt"] += " 特別警告：用戶目前走『劫財』運，對方極可能是針對資產而來，請強力勸阻任何金錢或事業上的交集。"
            
            return result

        return default_result

# 建立全域單例
engine = DynamicToneEngine()

def analyze_tone_strategy(user_input, bazi_info=None):
    return engine.analyze(user_input, bazi_info)
