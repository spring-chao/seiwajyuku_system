"""
学员分层模型 (Student Stratification Model)

五层分层体系：
- 🌟 核心层 (Core)    ≥85分  明星学员
- 💪 稳定层 (Stable)   70-84  中坚力量
- 🌱 潜力层 (Potential) 50-69 潜力学员
- ⚠️ 待激活 (At-Risk)  30-49  需要关注
- 🔴 流失风险 (Dormant) <30    近于休眠

评分维度：
1. 活动参与度 (30分) — 各类活动出勤率加权
2. 阅读投入度 (20分) — 打卡连续性和分享质量
3. 近期趋势 (25分)   — 近3个月 vs 更早时期的趋势
4. 参与广度 (25分)   — 参与活动类型的多样性
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from database import get_connection, execute_query, table_to_df


def get_stratification_weights() -> Dict[str, float]:
    """从配置获取分层权重"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM system_config WHERE key='stratification_weights'")
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return {"participation": 30, "reading": 20, "trend": 25, "diversity": 25}


def get_thresholds() -> Dict[str, float]:
    """获取分层阈值"""
    conn = get_connection()
    cur = conn.cursor()
    thresholds = {}
    for key in ['threshold_core', 'threshold_stable', 'threshold_potential', 'threshold_at_risk']:
        cur.execute("SELECT value FROM system_config WHERE key=?", (key,))
        row = cur.fetchone()
        thresholds[key] = float(row[0]) if row else 85.0
    conn.close()
    return thresholds


# ============================================================
# 维度一：活动参与度评分 (0-30分)
# ============================================================

def _score_participation(member_id: int, weights: Dict) -> float:
    """
    计算活动参与度得分
    
    各活动权重：
    - 小组学习会 40%（最核心活动）
    - 班级学习会 20%
    - 课程参与 20%
    - 报告会 10%（含发言加分）
    - 游学 10%
    """
    conn = get_connection()
    cur = conn.cursor()

    activity_weights = {
        'group_session': 0.40,
        'class_session': 0.20,
        'course': 0.20,
        'report_meeting': 0.10,
        'study_tour': 0.10,
    }

    total_score = 0.0

    for activity, aw in activity_weights.items():
        if activity == 'group_session':
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
                FROM group_sessions WHERE member_id=?
            """, (member_id,))
            stats = dict(cur.fetchone())
            rate = stats['present'] / stats['total'] if stats['total'] > 0 else 0

        elif activity == 'class_session':
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
                FROM class_sessions WHERE member_id=?
            """, (member_id,))
            stats = dict(cur.fetchone())
            rate = stats['present'] / stats['total'] if stats['total'] > 0 else 0

        elif activity == 'course':
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
                FROM courses WHERE member_id=?
            """, (member_id,))
            stats = dict(cur.fetchone())
            rate = stats['present'] / stats['total'] if stats['total'] > 0 else 0

        elif activity == 'report_meeting':
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present,
                       SUM(has_speech) as speeches
                FROM report_meetings WHERE member_id=?
            """, (member_id,))
            stats = dict(cur.fetchone())
            rate = stats['present'] / stats['total'] if stats['total'] > 0 else 0
            # 发言额外加分（最多加满100%）
            speech_bonus = min(stats['speeches'] * 0.15, 0.3) if stats['total'] > 0 else 0
            rate = min(rate + speech_bonus, 1.0)

        elif activity == 'study_tour':
            cur.execute("""
                SELECT COUNT(*) as total FROM study_tours WHERE member_id=?
            """, (member_id,))
            stats = dict(cur.fetchone())
            # 游学不是常规活动，按参与次数计分
            rate = min(stats['total'] * 0.25, 1.0)  # 4次以上满分

        total_score += rate * aw

    conn.close()

    # 转换为30分制
    max_score = weights.get('participation', 30)
    return round(total_score * max_score, 1)


# ============================================================
# 维度二：阅读投入度评分 (0-20分)
# ============================================================

def _score_reading(member_id: int, weights: Dict) -> float:
    """
    计算阅读投入度得分
    
    子维度：
    - 打卡连续性 50%
    - 分享质量 30%
    - 阅读多样性 20%
    """
    conn = get_connection()
    cur = conn.cursor()

    # 1. 打卡连续性 (50%)
    cur.execute("""
        SELECT checkin_date FROM reading_checkins
        WHERE member_id=? ORDER BY checkin_date
    """, (member_id,))
    checkin_dates = [dict(r)['checkin_date'] for r in cur.fetchall()]

    continuity_score = 0
    if len(checkin_dates) >= 2:
        # 计算连续打卡率
        dates_set = set(checkin_dates)
        max_streak = 1
        current_streak = 1
        sorted_dates = sorted(dates_set)
        for i in range(1, len(sorted_dates)):
            d1 = datetime.strptime(sorted_dates[i-1], '%Y-%m-%d')
            d2 = datetime.strptime(sorted_dates[i], '%Y-%m-%d')
            if (d2 - d1).days <= 2:  # 允许1天间隔
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        # 连续10天以上满分
        continuity_score = min(max_streak / 10, 1.0)
    elif len(checkin_dates) == 1:
        continuity_score = 0.1

    # 2. 分享质量 (30%)
    cur.execute("""
        SELECT COUNT(*) as total, AVG(quality_score) as avg_q
        FROM reading_shares WHERE member_id=?
    """, (member_id,))
    share_stats = dict(cur.fetchone())
    share_count = share_stats['total'] or 0
    avg_quality = share_stats['avg_q'] or 0

    # 分享次数得分（5次以上满分）
    share_freq = min(share_count / 5, 1.0)
    # 质量得分
    quality = avg_quality / 5 if avg_quality > 0 else 0
    share_score = share_freq * 0.5 + quality * 0.5

    # 3. 阅读多样性 (20%)
    cur.execute("""
        SELECT COUNT(DISTINCT book_name) as unique_books
        FROM reading_checkins WHERE member_id=?
    """, (member_id,))
    books = dict(cur.fetchone())['unique_books'] or 0
    diversity_score = min(books / 5, 1.0)  # 5本不同书满分

    # 综合(20分制)
    composite = continuity_score * 0.5 + share_score * 0.3 + diversity_score * 0.2
    max_score = weights.get('reading', 20)
    return round(composite * max_score, 1)


# ============================================================
# 维度三：近期趋势评分 (0-25分)
# ============================================================

def _score_trend(member_id: int, weights: Dict) -> float:
    """
    计算近期趋势得分
    
    对比近3个月 vs 更早时期的参与率变化
    - 上升趋势: 加分
    - 持平: 维持
    - 下降趋势: 减分
    """
    conn = get_connection()
    cur = conn.cursor()

    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')

    # 收集所有活动的近期 vs 远期参与率
    # 注意：不同表的日期列名不同
    table_configs = [
        ('group_sessions', 'session_date'),
        ('class_sessions', 'session_date'),
        ('courses', 'course_date'),
        ('report_meetings', 'meeting_date'),
    ]

    recent_rates = []
    older_rates = []

    for table, date_col in table_configs:
        # 近期 (近3个月)
        cur.execute(f"""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
            FROM {table}
            WHERE member_id=? AND {date_col}>=?
        """, (member_id, three_months_ago))
        recent = dict(cur.fetchone())

        # 远期 (3个月之前)
        cur.execute(f"""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
            FROM {table}
            WHERE member_id=? AND {date_col}<? AND {date_col}!=''
        """, (member_id, three_months_ago))
        older = dict(cur.fetchone())

        if recent['total'] > 0:
            recent_rates.append(recent['present'] / recent['total'])
        if older['total'] > 0:
            older_rates.append(older['present'] / older['total'])

    # 也看读书打卡趋势
    cur.execute(f"""
        SELECT COUNT(*) as recent_count FROM reading_checkins
        WHERE member_id=? AND checkin_date>=?
    """, (member_id, three_months_ago))
    recent_checkin = cur.fetchone()[0]

    cur.execute(f"""
        SELECT COUNT(*) as older_count FROM reading_checkins
        WHERE member_id=? AND checkin_date<? AND checkin_date!=''
    """, (member_id, three_months_ago))
    older_checkin = cur.fetchone()[0]

    conn.close()

    # 计算平均参与率
    avg_recent = np.mean(recent_rates) if recent_rates else 0
    avg_older = np.mean(older_rates) if older_rates else 0

    # 读书打卡变化
    checkin_change = 0
    if older_checkin > 0:
        checkin_change = (recent_checkin - older_checkin) / older_checkin
    elif recent_checkin > 0:
        checkin_change = 1  # 从无到有是好的

    # 参与率变化
    rate_change = avg_recent - avg_older

    # 综合趋势分(-1 to 1)
    trend = rate_change * 0.7 + min(checkin_change, 1) * 0.3
    # 映射到0-1分
    trend_score = max(0, min(1, 0.5 + trend))

    max_score = weights.get('trend', 25)
    return round(trend_score * max_score, 1)


# ============================================================
# 维度四：参与广度评分 (0-25分)
# ============================================================

def _score_diversity(member_id: int, weights: Dict) -> float:
    """
    计算参与广度得分
    
    参与的活动类型越多，得分越高
    也考虑在活动中的角色深度
    """
    conn = get_connection()
    cur = conn.cursor()

    # 检查参与了哪些类型的活动
    activity_types = []

    cur.execute("SELECT COUNT(*) as c FROM group_sessions WHERE member_id=? AND attendance='present'", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('group')

    cur.execute("SELECT COUNT(*) as c FROM class_sessions WHERE member_id=? AND attendance='present'", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('class')

    cur.execute("SELECT COUNT(*) as c FROM courses WHERE member_id=? AND attendance='present'", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('course')

    cur.execute("SELECT COUNT(*) as c FROM report_meetings WHERE member_id=? AND attendance='present'", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('report')

    cur.execute("SELECT COUNT(*) as c FROM study_tours WHERE member_id=?", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('tour')

    cur.execute("SELECT COUNT(*) as c FROM reading_checkins WHERE member_id=?", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('checkin')

    cur.execute("SELECT COUNT(*) as c FROM reading_shares WHERE member_id=?", (member_id,))
    if cur.fetchone()[0] > 0:
        activity_types.append('share')

    # 角色深度: 是否担任过组织者/主持人/发言
    cur.execute("""
        SELECT COUNT(*) as c FROM class_sessions
        WHERE member_id=? AND role IN ('speaker','organizer')
    """, (member_id,))
    has_role = cur.fetchone()[0] > 0

    cur.execute("""
        SELECT COUNT(*) as c FROM report_meetings
        WHERE member_id=? AND has_speech=1
    """, (member_id,))
    has_speech = cur.fetchone()[0] > 0

    conn.close()

    # 类型数量得分 (7大类型)
    type_score = len(activity_types) / 7.0

    # 角色深度加分 (最多加0.2)
    role_bonus = 0.1 if has_role else 0
    speech_bonus = 0.1 if has_speech else 0
    depth_score = min(type_score + role_bonus + speech_bonus, 1.0)

    max_score = weights.get('diversity', 25)
    return round(depth_score * max_score, 1)


# ============================================================
# 综合评分与分层
# ============================================================

LAYER_MAP = {
    'core': {'label': '🌟 核心层', 'range': (85, 100), 'desc': '明星学员，积极参与各类活动，持续成长'},
    'stable': {'label': '💪 稳定层', 'range': (70, 84), 'desc': '中坚力量，参与稳定，值得鼓励'},
    'potential': {'label': '🌱 潜力层', 'range': (50, 69), 'desc': '有潜力，需针对性引导提升参与度'},
    'at_risk': {'label': '⚠️ 待激活', 'range': (30, 49), 'desc': '参与度偏低，需要主动关怀和激活'},
    'dormant': {'label': '🔴 流失风险', 'range': (0, 29), 'desc': '长期未参与，面临流失风险'},
}


def calculate_member_score(member_id: int) -> Dict:
    """计算单个学员的综合评分和各维度得分"""
    weights = get_stratification_weights()

    participation = _score_participation(member_id, weights)
    reading = _score_reading(member_id, weights)
    trend = _score_trend(member_id, weights)
    diversity = _score_diversity(member_id, weights)

    total = round(participation + reading + trend + diversity, 1)

    # 确定分层
    thresholds = get_thresholds()
    if total >= thresholds['threshold_core']:
        layer = 'core'
    elif total >= thresholds['threshold_stable']:
        layer = 'stable'
    elif total >= thresholds['threshold_potential']:
        layer = 'potential'
    elif total >= thresholds['threshold_at_risk']:
        layer = 'at_risk'
    else:
        layer = 'dormant'

    return {
        'member_id': member_id,
        'total_score': total,
        'layer': layer,
        'layer_label': LAYER_MAP[layer]['label'],
        'layer_desc': LAYER_MAP[layer]['desc'],
        'dimensions': {
            'participation': {'score': participation, 'max': weights['participation'],
                              'label': '活动参与度', 'description': '各类活动出勤率加权计算'},
            'reading': {'score': reading, 'max': weights['reading'],
                        'label': '阅读投入度', 'description': '打卡连续性、分享质量与阅读多样性'},
            'trend': {'score': trend, 'max': weights['trend'],
                      'label': '近期趋势', 'description': '近3个月vs历史参与趋势变化'},
            'diversity': {'score': diversity, 'max': weights['diversity'],
                          'label': '参与广度', 'description': '参与活动类型多样性与角色深度'},
        }
    }


def calculate_all_members_scores() -> List[Dict]:
    """计算所有活跃学员的综合评分"""
    members = execute_query(
        "SELECT id, name, class_name, center FROM members WHERE status='active'"
    )
    results = []
    for m in members:
        score = calculate_member_score(m['id'])
        score['name'] = m['name']
        score['class_name'] = m['class_name']
        score['center'] = m['center']
        results.append(score)
    return results


def get_layer_statistics() -> Dict:
    """获取各分层的人数统计"""
    scores = calculate_all_members_scores()
    stats = {k: 0 for k in LAYER_MAP}
    for s in scores:
        stats[s['layer']] += 1
    total = len(scores)
    percentages = {}
    for k, v in stats.items():
        percentages[k] = round(v / total * 100, 1) if total > 0 else 0
    return {
        'counts': stats,
        'percentages': percentages,
        'total': total,
        'layer_info': LAYER_MAP,
    }


def get_weak_dimensions(member_score: Dict) -> List[Dict]:
    """找出学员的薄弱维度（得分率 < 60% 的维度）"""
    weak = []
    for dim_name, dim_data in member_score['dimensions'].items():
        ratio = dim_data['score'] / dim_data['max'] if dim_data['max'] > 0 else 0
        if ratio < 0.6:
            weak.append({
                'name': dim_name,
                'label': dim_data['label'],
                'score': dim_data['score'],
                'max': dim_data['max'],
                'ratio': round(ratio * 100, 1),
                'description': dim_data['description'],
            })
    return sorted(weak, key=lambda x: x['ratio'])


if __name__ == "__main__":
    # 测试
    from database import init_database
    init_database()
    print(get_layer_statistics())
