import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, List
import threading

_EMOTION_LEXICON = {
    "joy": ["开心", "高兴", "快乐", "喜悦", "幸福", "满意", "喜欢", "棒", "赞", "haha", "lol", "great", "awesome", "happy", "joy"],
    "anger": ["生气", "愤怒", "气死", "火大", "怒", "气人", "恼火", "靠", "md", "shit", "angry", "rage"],
    "sadness": ["难过", "悲伤", "伤心", "失望", "伤感", "心塞", "郁闷", "哭", "sad", "down"],
    "fear": ["害怕", "恐惧", "担心", "紧张", "不安", "怕", "慌", "scared", "fear"],
    "love": ["爱", "喜欢你", "爱你", "拥抱", "亲", "真心", "感激", "感谢", "love", "luv", "dear"],
    "surprise": ["惊讶", "意外", "哇", "卧槽", "竟然", "没想到", "惊喜", "wow", "surprised"]
}

_PRECOMPILED_PATTERNS = {}
for label, words in _EMOTION_LEXICON.items():
    _PRECOMPILED_PATTERNS[label] = [w.lower() for w in words]

def _get_catlike_dir() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    catlike_dir = os.path.join(base_dir, "catlike")
    os.makedirs(catlike_dir, exist_ok=True)
    return catlike_dir

class EmotionAnalyzer:
    def __init__(self, api_key: str = None):
        self.emotion_labels = ["anger", "joy", "love", "sadness", "fear", "surprise"]
        self._score_history: List[Dict] = []
        self._max_history = 100
        self._segment_count = 0
        self._current_segment: List[Dict] = []
        self._lock = threading.Lock()
        self._catlike_dir = _get_catlike_dir()
    
    def analyze(self, text: str) -> Dict:
        if not text or not text.strip():
            return self._neutral_result()
        try:
            s = text.strip().lower()
            if len(s) > 512:
                s = s[:512]
            
            scores = {label: 0.0 for label in self.emotion_labels}
            
            for label, patterns in _PRECOMPILED_PATTERNS.items():
                c = 0
                for w in patterns:
                    c += s.count(w)
                if label in scores:
                    scores[label] = float(c)
            
            total = sum(scores.values())
            if total > 0:
                for k in scores:
                    scores[k] = round(scores[k] / total, 4)
                dominant = max(scores.items(), key=lambda x: x[1])
            else:
                return self._neutral_result()
            
            emotion_data = {
                "dominant_emotion": dominant[0] if total > 0 else "neutral",
                "dominant_score": round(dominant[1], 4) if total > 0 else 0.5,
                "all_scores": {k: round(v, 4) for k, v in scores.items()},
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text)
            }
            
            with self._lock:
                self._add_to_history(emotion_data)
                self._current_segment.append(emotion_data)
                self._segment_count += 1
                
                if self._segment_count >= 5:
                    self._generate_segment_log()
                    self._segment_count = 0
                    self._current_segment = []
            
            return emotion_data
            
        except Exception as e:
            print(f"[EmotionAnalyzer] 分析失败: {e}")
            return self._neutral_result()
    
    def _neutral_result(self) -> Dict:
        return {
            "dominant_emotion": "neutral",
            "dominant_score": 0.5,
            "all_scores": {label: 1/6 for label in self.emotion_labels},
            "timestamp": datetime.now().isoformat(),
            "text_length": 0
        }
    
    def _add_to_history(self, data: Dict):
        self._score_history.append(data)
        if len(self._score_history) > self._max_history:
            self._score_history = self._score_history[-self._max_history:]
    
    def get_history(self) -> List[Dict]:
        with self._lock:
            return self._score_history.copy()
    
    def get_average_scores(self) -> Dict:
        with self._lock:
            if not self._score_history:
                return {label: 0.0 for label in self.emotion_labels}
            
            totals = {label: 0.0 for label in self.emotion_labels}
            for record in self._score_history:
                for label, score in record.get("all_scores", {}).items():
                    totals[label] += score
            
            count = len(self._score_history)
            return {label: round(total / count, 4) for label, total in totals.items()}
    
    def _get_segment_scores(self, segment: List[Dict]) -> Dict:
        if not segment:
            return {label: 0.0 for label in self.emotion_labels}
        
        totals = {label: 0.0 for label in self.emotion_labels}
        for record in segment:
            for label, score in record.get("all_scores", {}).items():
                totals[label] += score
        
        count = len(segment)
        return {label: round(total / count, 4) for label, total in totals.items()}
    
    def _generate_segment_log(self):
        output_path = os.path.join(self._catlike_dir, "face.log")
        avg_scores = self._get_segment_scores(self._current_segment)
        total_interactions = len(self._current_segment)
        
        emotion_intensity = {
            "joy": max(0, avg_scores.get("joy", 0) - 0.2) * 1.25,
            "anger": avg_scores.get("anger", 0) * 1.1,
            "sadness": avg_scores.get("sadness", 0) * 1.1,
            "fear": avg_scores.get("fear", 0) * 1.0,
            "love": avg_scores.get("love", 0) * 1.15,
            "surprise": avg_scores.get("surprise", 0) * 1.0
        }
        
        warmth = round((emotion_intensity.get("joy", 0) * 0.4 + emotion_intensity.get("love", 0) * 0.4 - emotion_intensity.get("anger", 0) * 0.1 - emotion_intensity.get("fear", 0) * 0.1) * 100, 1)
        empathy = round((emotion_intensity.get("sadness", 0) * 0.3 + emotion_intensity.get("love", 0) * 0.3 + emotion_intensity.get("joy", 0) * 0.2 + emotion_intensity.get("surprise", 0) * 0.2) * 100, 1)
        energy = round((emotion_intensity.get("joy", 0) * 0.35 + emotion_intensity.get("surprise", 0) * 0.25 + emotion_intensity.get("anger", 0) * 0.2 + emotion_intensity.get("fear", 0) * 0.2) * 100, 1)
        stability = round((1.0 - emotion_intensity.get("anger", 0) * 0.4 - emotion_intensity.get("fear", 0) * 0.3 - emotion_intensity.get("surprise", 0) * 0.3) * 100, 1)
        positivity = round((emotion_intensity.get("joy", 0) * 0.5 + emotion_intensity.get("love", 0) * 0.3 - emotion_intensity.get("anger", 0) * 0.1 - emotion_intensity.get("sadness", 0) * 0.1) * 100, 1)
        
        warmth = max(0, min(100, warmth))
        empathy = max(0, min(100, empathy))
        energy = max(0, min(100, energy))
        stability = max(0, min(100, stability))
        positivity = max(0, min(100, positivity))
        
        dominant_emotion = "neutral"
        max_score = 0
        for emotion, score in avg_scores.items():
            if score > max_score:
                max_score = score
                dominant_emotion = emotion
        
        log_content = f"""================================================================================
                           皮皮AI 情感分析报告 (最近5条)
================================================================================
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
本段交互次数: {total_interactions}

--------------------------------------------------------------------------------
情感分布评分 (0-100分):
--------------------------------------------------------------------------------
  快乐度 (Joy):      {avg_scores.get('joy', 0)*100:6.1f}%
  愤怒值 (Anger):    {avg_scores.get('anger', 0)*100:6.1f}%
  悲伤度 (Sadness):  {avg_scores.get('sadness', 0)*100:6.1f}%
  恐惧感 (Fear):     {avg_scores.get('fear', 0)*100:6.1f}%
  爱意值 (Love):     {avg_scores.get('love', 0)*100:6.1f}%
  惊讶度 (Surprise): {avg_scores.get('surprise', 0)*100:6.1f}%

--------------------------------------------------------------------------------
综合拟人化评分:
--------------------------------------------------------------------------------
  温暖度: {warmth:5.1f}/100  (共情能力与情感表达)
  同理心: {empathy:5.1f}/100  (理解用户情绪的程度)
  活力值: {energy:5.1f}/100  (回复的积极程度)
  稳定度: {stability:5.1f}/100  (情绪波动稳定性)
  正面度: {positivity:5.1f}/100  (整体情感倾向)

--------------------------------------------------------------------------------
主导情感: {dominant_emotion.upper()}
================================================================================
"""
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"[EmotionAnalyzer] 阶段日志已更新: {output_path}")
        except Exception as e:
            print(f"[EmotionAnalyzer] 写入失败: {e}")
        
        self._append_to_total_log(avg_scores, total_interactions, dominant_emotion)
    
    def _append_to_total_log(self, avg_scores: Dict, total_interactions: int, dominant_emotion: str):
        output_path = os.path.join(self._catlike_dir, "face_total.log")
        
        new_entry = f"""================================================================================
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
交互次数: {total_interactions}
主导情感: {dominant_emotion.upper()}
情感分布:
  快乐度: {avg_scores.get('joy', 0)*100:.1f}% | 愤怒值: {avg_scores.get('anger', 0)*100:.1f}% | 悲伤度: {avg_scores.get('sadness', 0)*100:.1f}%
  恐惧感: {avg_scores.get('fear', 0)*100:.1f}% | 爱意值: {avg_scores.get('love', 0)*100:.1f}% | 惊讶度: {avg_scores.get('surprise', 0)*100:.1f}%
================================================================================

"""
        
        try:
            with open(output_path, 'a', encoding='utf-8') as f:
                f.write(new_entry)
            print(f"[EmotionAnalyzer] 总日志已追加: {output_path}")
        except Exception as e:
            print(f"[EmotionAnalyzer] 追加总日志失败: {e}")
    
    def generate_face_log(self, output_path: str = None) -> str:
        if output_path is None:
            output_path = os.path.join(self._catlike_dir, "face.log")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with self._lock:
            avg_scores = self.get_average_scores()
            total_interactions = len(self._score_history)
        
        emotion_intensity = {
            "joy": max(0, avg_scores.get("joy", 0) - 0.2) * 1.25,
            "anger": avg_scores.get("anger", 0) * 1.1,
            "sadness": avg_scores.get("sadness", 0) * 1.1,
            "fear": avg_scores.get("fear", 0) * 1.0,
            "love": avg_scores.get("love", 0) * 1.15,
            "surprise": avg_scores.get("surprise", 0) * 1.0
        }
        
        warmth = round((emotion_intensity.get("joy", 0) * 0.4 + emotion_intensity.get("love", 0) * 0.4 - emotion_intensity.get("anger", 0) * 0.1 - emotion_intensity.get("fear", 0) * 0.1) * 100, 1)
        empathy = round((emotion_intensity.get("sadness", 0) * 0.3 + emotion_intensity.get("love", 0) * 0.3 + emotion_intensity.get("joy", 0) * 0.2 + emotion_intensity.get("surprise", 0) * 0.2) * 100, 1)
        energy = round((emotion_intensity.get("joy", 0) * 0.35 + emotion_intensity.get("surprise", 0) * 0.25 + emotion_intensity.get("anger", 0) * 0.2 + emotion_intensity.get("fear", 0) * 0.2) * 100, 1)
        stability = round((1.0 - emotion_intensity.get("anger", 0) * 0.4 - emotion_intensity.get("fear", 0) * 0.3 - emotion_intensity.get("surprise", 0) * 0.3) * 100, 1)
        positivity = round((emotion_intensity.get("joy", 0) * 0.5 + emotion_intensity.get("love", 0) * 0.3 - emotion_intensity.get("anger", 0) * 0.1 - emotion_intensity.get("sadness", 0) * 0.1) * 100, 1)
        
        warmth = max(0, min(100, warmth))
        empathy = max(0, min(100, empathy))
        energy = max(0, min(100, energy))
        stability = max(0, min(100, stability))
        positivity = max(0, min(100, positivity))
        
        dominant_emotion = "neutral"
        max_score = 0
        for emotion, score in avg_scores.items():
            if score > max_score:
                max_score = score
                dominant_emotion = emotion
        
        log_content = f"""================================================================================
                          皮皮AI 情感分析报告
================================================================================
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总交互次数: {total_interactions}

--------------------------------------------------------------------------------
情感分布评分 (0-100分):
--------------------------------------------------------------------------------
  快乐度 (Joy):      {avg_scores.get('joy', 0)*100:6.1f}%
  愤怒值 (Anger):    {avg_scores.get('anger', 0)*100:6.1f}%
  悲伤度 (Sadness):  {avg_scores.get('sadness', 0)*100:6.1f}%
  恐惧感 (Fear):     {avg_scores.get('fear', 0)*100:6.1f}%
  爱意值 (Love):     {avg_scores.get('love', 0)*100:6.1f}%
  惊讶度 (Surprise): {avg_scores.get('surprise', 0)*100:6.1f}%

--------------------------------------------------------------------------------
综合拟人化评分:
--------------------------------------------------------------------------------
  温暖度: {warmth:5.1f}/100  (共情能力与情感表达)
  同理心: {empathy:5.1f}/100  (理解用户情绪的程度)
  活力值: {energy:5.1f}/100  (回复的积极程度)
  稳定度: {stability:5.1f}/100  (情绪波动稳定性)
  正面度: {positivity:5.1f}/100  (整体情感倾向)

--------------------------------------------------------------------------------
主导情感: {dominant_emotion.upper()}
================================================================================
"""
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"[EmotionAnalyzer] face.log已生成: {output_path}")
        except Exception as e:
            print(f"[EmotionAnalyzer] 写入失败: {e}")
        
        return output_path


_emotion_analyzer_instance: Optional[EmotionAnalyzer] = None
_instance_lock = threading.Lock()

def get_emotion_analyzer(api_key: str = None) -> Optional[EmotionAnalyzer]:
    global _emotion_analyzer_instance
    with _instance_lock:
        if _emotion_analyzer_instance is None:
            _emotion_analyzer_instance = EmotionAnalyzer(api_key)
    return _emotion_analyzer_instance

def analyze_user_emotion(text: str) -> Dict:
    analyzer = get_emotion_analyzer()
    return analyzer.analyze(text)

def generate_face_log(api_key: str = None, output_path: str = None) -> str:
    analyzer = get_emotion_analyzer(api_key)
    return analyzer.generate_face_log(output_path)
