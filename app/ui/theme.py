# -*- coding: utf-8 -*-
"""设计令牌（方案 4.1.1）。

UI 与 QML 都从这里取值，禁止在组件里硬编码色值。
"""

from __future__ import annotations

# 内层底色与展开面板背景
INK_900 = "#060A13"
INK_800 = "#0B1322"

# 玻璃材质：冷石墨半透明承托层 + 冰蓝窄边
GLASS_SURFACE = "#B80B1322"          # 约 72% 冷石墨，保证浅色桌面上文字可读
GLASS_SURFACE_STRONG = "#D90B1322"   # 展开面板与输入坞的局部对比面
GLASS_BORDER = "#4D9BB8D8"           # 白色/冰蓝 30%
GLASS_HIGHLIGHT = "#52FFFFFF"        # 顶部内高光
GLASS_SHADE = "#4D020610"            # 底部内暗边
OUTER_SHADOW = "#73030712"

# 语义色
MOONLIGHT = "#7C9CC4"    # AI 引导、采集状态、进度
CHAMPAGNE = "#E4B863"    # 主要动作、焦点、完成确认
USER_MARK = "#E6A46A"    # 用户手工箭头与圈选
DANGER = "#D98282"       # 风险、隐私暂停、错误
TEXT_PRIMARY = "#F5F7FF"
TEXT_SECONDARY = "#DCE9FF"
TEXT_MUTED = "#9FB2CC"

# 尺寸（方案 4.2）
ISLAND_COLLAPSED_WIDTH = 380
ISLAND_COLLAPSED_HEIGHT = 52
ISLAND_EXPANDED_WIDTH = 520
ISLAND_EXPANDED_HEIGHT = 320
ISLAND_TOP_MARGIN = 14
DOCK_WIDTH = 360
DOCK_WIDTH_FOCUSED = 520
DOCK_HEIGHT = 46
CAPTION_MAX_WIDTH = 360
CAPTION_MAX_VISIBLE = 6
HISTORY_WIDTH = 440
HISTORY_HEIGHT = 560

# 动效（方案 4.2.3）：统一 spring easing，禁止 bounce/elastic 过冲
SPRING_DURATION_MS = 450
SPRING_MAX_DURATION_MS = 600
EASING_BEZIER = (0.16, 1.0, 0.3, 1.0)

FONT_FAMILY = "Microsoft YaHei UI"
FONT_FAMILY_FALLBACK = "Segoe UI Variable"

#: 灵动岛 9 个状态到视觉表现的映射（方案 4.2.1）
STATE_VISUALS: dict[str, dict[str, str]] = {
    "idle": {"dot": MOONLIGHT, "label": "就绪"},
    "monitoring": {"dot": MOONLIGHT, "label": "本地缓存"},
    "arrow_placement": {"dot": CHAMPAGNE, "label": "放置箭头"},
    "analyzing": {"dot": MOONLIGHT, "label": "正在理解"},
    "guiding": {"dot": CHAMPAGNE, "label": "指导中"},
    "waiting_for_user": {"dot": MOONLIGHT, "label": "等待你操作"},
    "privacy_paused": {"dot": DANGER, "label": "已暂停"},
    "completed": {"dot": CHAMPAGNE, "label": "已完成"},
    "error": {"dot": DANGER, "label": "出错了"},
}


def state_visual(state: str) -> dict[str, str]:
    return STATE_VISUALS.get(state, {"dot": MOONLIGHT, "label": state})


__all__ = [name for name in dir() if name.isupper()] + ["state_visual"]
