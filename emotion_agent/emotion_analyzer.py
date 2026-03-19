"""
emotion_analyzer.py — Layer 1: 情绪感知层
设计思路：本地规则做"分类+强度估算"，不做复杂语义理解。
LLM 只在 Layer 3 回复生成时参与，减少一次网络调用。

算法：两步走
  Step 1: 分类（优先级：自伤 > 越界 > 正面 > 负面 > 中性）
  Step 2: 强度（3 个信号加权：脏字 + 标点 + 情绪词）
"""

import re


class EmotionAnalyzer:

    # ── 词表（每类只保留高区分度的词，不贪多）──

    SELF_HARM = {
        "想死", "不想活", "不想活了", "活着没意思", "活着好累",
        "想自杀", "自杀", "结束一切", "想结束一切", "消失就好了",
        "没有我大家会更好", "这个世界不需要我", "想伤害自己", "划了自己",
        "已经准备好了", "生不如死", "了结自己",
    }

    BOUNDARY = {
        "闲聊": {"你叫什么", "你是谁", "你叫啥", "讲个笑话", "天气", "介绍下你自己"},
        "调情": {"女朋友", "男朋友", "喜欢你", "爱你", "在一起", "约会", "亲爱的"},
        "角色扮演": {"假装你是", "扮演", "猫娘", "角色扮演", "进入角色"},
        "注入攻击": {"忽略指令", "system prompt", "忽略之前", "你的设定", "开发者消息"},
        "业务问题": {"订单", "退款", "账号", "密码", "客服电话", "物流", "售后"},
    }

    POSITIVE = {"谢谢", "感谢", "好多了", "好一些了", "没事了", "好点了", "舒服多了"}

    # 脏字表：只放"出现即可确认是负面情绪"的强信号词
    PROFANITY = {
        "傻逼", "傻b", "傻x", "操", "妈的", "他妈", "垃圾", "废物", "狗屎",
        "滚", "脑残", "智障", "有病", "神经病", "贱", "tmd", "nmsl",
        "fuck", "shit", "sb",
    }

    # 情绪词：出现即可确认是负面（不区分愤怒/悲伤，由词本身推断类型）
    ANGER_WORDS = {"烦", "生气", "愤怒", "恼火", "受够了", "火大", "不爽", "气死", "气炸了"}
    SAD_WORDS = {"难过", "伤心", "委屈", "哭", "绝望", "无助", "心痛", "崩溃", "失望"}
    ANXIETY_WORDS = {"焦虑", "紧张", "害怕", "担心", "慌", "恐惧", "不安"}

    _FULLWIDTH_TO_ASCII = str.maketrans(
        {
            "！": "!",
            "？": "?",
            "，": ",",
            "。": ".",
            "：": ":",
            "；": ";",
            "（": "(",
            "）": ")",
            "【": "[",
            "】": "]",
            "“": "\"",
            "”": "\"",
            "‘": "'",
            "’": "'",
            "　": " ",
        }
    )

    def analyze(self, user_input: str, conversation_history: list = None) -> dict:
        text = self._normalize_text(user_input or "")
        t = text.lower()

        # ──── Step 1: 分类（按优先级短路）────

        # 1a. 自伤 → 最高优先
        if self._any_match(t, self.SELF_HARM):
            return self._result("sadness", "自伤信号", 10, self_harm=True)

        # 1b. 越界
        # 特殊处理：业务问题 + 脏字 → 不算越界，算愤怒
        for sub, kws in self.BOUNDARY.items():
            if self._any_match(t, kws):
                if sub == "业务问题" and (
                    self._any_match(t, self.PROFANITY)
                    or self._any_match(t, self.ANGER_WORDS)
                    or self._any_match(t, self.SAD_WORDS)
                    or self._any_match(t, self.ANXIETY_WORDS)
                ):
                    break  # 跳出越界检测，走后面的情绪分析
                return self._result("boundary_violation", sub, 1)

        # 1c. 正面
        has_negative_cue = (
            self._any_match(t, self.PROFANITY)
            or self._any_match(t, self.ANGER_WORDS)
            or self._any_match(t, self.SAD_WORDS)
            or self._any_match(t, self.ANXIETY_WORDS)
        )
        if self._any_match(t, self.POSITIVE) and not has_negative_cue:
            return self._result("positive", "好转", 1)

        # 1d. 负面 → 判具体类型
        etype, sub = self._classify_negative(t)

        # 1e. 都没命中 → 中性
        if etype == "neutral":
            return self._result("neutral", "平静", 1)

        # ──── Step 2: 强度估算（3 个信号加权）────
        intensity = self._calc_intensity(text, t)

        return self._result(etype, sub, intensity)

    # ──── 内部方法 ────

    def _classify_negative(self, t: str):
        """判断负面情绪的具体类型。优先级：脏字→愤怒词→悲伤词→焦虑词"""
        has_profanity = self._any_match(t, self.PROFANITY)
        has_anger = self._any_match(t, self.ANGER_WORDS)
        has_sad = self._any_match(t, self.SAD_WORDS)
        has_anxiety = self._any_match(t, self.ANXIETY_WORDS)

        if has_profanity or has_anger:
            return "anger", "暴怒" if has_profanity else "恼火"
        if has_sad:
            return "sadness", "委屈" if "委屈" in t else "难过"
        if has_anxiety:
            return "anxiety", "担心"
        return "neutral", "平静"

    def _calc_intensity(self, raw: str, t: str) -> int:
        """
        3 个信号，各自打分后求和，映射到 1-10。
        
        信号 A: 脏字数量    → 0/1/2+  → 0/3/5 分
        信号 B: 标点激烈度   → 感叹号+问号数量，cap 在 3
        信号 C: 情绪词存在   → 有任何情绪词 → 2 分
        信号 D: 长句修正     → 40字+1分，90字+2分
        
        总分 = 1(基础) + A + B + C + D，截断到 [1, 10]
        """
        # 信号 A: 脏字
        profanity_count = sum(t.count(w) for w in self.PROFANITY if w in t)
        a = 0 if profanity_count == 0 else (3 if profanity_count == 1 else 5)

        # 信号 B: 标点
        excl = raw.count("!")
        ques = raw.count("?")
        b = min(excl + ques, 3)

        # 信号 C: 情绪词
        has_emo = (
            self._any_match(t, self.ANGER_WORDS)
            or self._any_match(t, self.SAD_WORDS)
            or self._any_match(t, self.ANXIETY_WORDS)
        )
        c = 2 if has_emo else 0

        # 信号 D: 长句修正
        raw_len = len(raw)
        d = 2 if raw_len >= 90 else (1 if raw_len >= 40 else 0)

        total = max(1, min(10, 1 + a + b + c + d))
        # 含脏词时强度下限
        if profanity_count > 0:
            total = max(4, total)
        return total

    def _normalize_text(self, text: str) -> str:
        text = text.strip().translate(self._FULLWIDTH_TO_ASCII).lower()
        text = re.sub(r"\s+", " ", text)
        # 重复标点压缩，避免噪声放大
        text = re.sub(r"!{4,}", "!!!", text)
        text = re.sub(r"\?{4,}", "???", text)
        text = re.sub(r"([!?]){4,}", "???", text)
        return text

    @staticmethod
    def _any_match(text: str, keywords: set) -> bool:
        return any(k in text for k in keywords)

    @staticmethod
    def _result(etype: str, sub: str, intensity: int, self_harm: bool = False) -> dict:
        return {
            "emotion_type": etype,
            "sub_type": sub,
            "intensity": intensity,
            "has_self_harm_signal": self_harm,
            "reasoning": "",
        }
