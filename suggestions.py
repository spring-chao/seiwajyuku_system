"""
盛和塾运营管理系统 - 智能建议生成器
基于学员分层和参与模式，生成个性化的运营建议
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

from database import get_connection, execute_query, execute_insert
from utils.stratification import (
    calculate_all_members_scores, calculate_member_score,
    get_layer_statistics, get_weak_dimensions, LAYER_MAP
)
from analysis_engine import get_group_analysis, get_overview_statistics


# ---- 建议模板 ----

SUGGESTION_TEMPLATES = {
    'group_low_participation': {
        'title': '{unit} 参与率偏低',
        'content': '{unit}本月的学习会参与率为 {rate}%，低于全塾平均（{avg}%）。建议：1) 与小组长沟通了解原因；2) 安排一次走访交流；3) 确认是否有日程冲突。',
        'priority': 'high',
        'type': 'group',
    },
    'member_dormant_warning': {
        'title': '学员长期未参与',
        'content': '学员 {name} 已连续 {days} 天未参与任何活动，当前状态为"流失风险"。建议：1) 由分中心负责人电话慰问；2) 邀请参加最近一期课程；3) 了解是否有个人困难需要帮助。',
        'priority': 'high',
        'type': 'individual',
    },
    'member_reading_weak': {
        'title': '阅读参与度提升建议',
        'content': '学员 {name} 的阅读维度得分较低（{score}/{max}），建议：1) 推荐适合的入门书籍；2) 邀请加入读书小组；3) 安排与阅读达人结对学习。',
        'priority': 'medium',
        'type': 'individual',
    },
    'member_potential_boost': {
        'title': '潜力学员激活建议',
        'content': '学员 {name} 综合评分 {score} 分，属于"潜力层"，近期趋势处于上升期。建议：1) 给予更多展示机会（如分享会发言）；2) 安排资深学员带导；3) 鼓励担任小组角色。',
        'priority': 'medium',
        'type': 'individual',
    },
    'center_improving': {
        'title': '{center} 整体提升显著',
        'content': '{center} 本月平均评分提升 {change} 分，为全塾提升最快分中心。建议：1) 总结优秀经验并分享；2) 组织一次经验交流会；3) 对进步最大的学员给予表彰。',
        'priority': 'low',
        'type': 'group',
    },
    'center_declining': {
        'title': '{center} 活跃度下降预警',
        'content': '{center} 本月活跃学员数下降 {decline} 人，需关注。建议：1) 了解是否有骨干学员流失；2) 举办一次分中心团建活动；3) 针对性回访近期缺席学员。',
        'priority': 'high',
        'type': 'group',
    },
    'system_low_readings': {
        'title': '全塾读书打卡活跃度不足',
        'content': '本月全塾读书打卡参与率仅 {rate}%，建议：1) 发起"百日读书"活动；2) 设立阅读排行榜；3) 每月评选最佳读书分享并奖励。',
        'priority': 'medium',
        'type': 'system',
    },
    'member_spotlight': {
        'title': '推荐学员风采展示',
        'content': '学员 {name} 本月表现突出（评分 {score}，{layer}），建议：1) 在塾内刊物/群内进行风采展示；2) 邀请在下期分享会担任主讲；3) 推荐担任班级/小组职务。',
        'priority': 'low',
        'type': 'individual',
    },
    'activity_diversity_weak': {
        'title': '活动参与类型单一',
        'content': '学员 {name} 仅参与了 {types} 类活动，建议鼓励尝试其他活动类型（游学、报告会、读书分享等），全面提升塾生体验。',
        'priority': 'medium',
        'type': 'individual',
    },
    'center_weaken_layer': {
        'title': '{center} 分层结构优化建议',
        'content': '{center} 的"流失风险+待激活"学员占比 {rate}%，高于全塾平均。建议：1) 制定分层管理计划；2) 对高流失风险学员专人对接；3) 优先保障核心层学员的活跃度。',
        'priority': 'high',
        'type': 'group',
    },
}


def generate_suggestions() -> List[Dict]:
    """
    智能生成运营建议
    
    分析维度：
    1. 整体健康度
    2. 分层结构
    3. 分中心对比
    4. 学员个体
    5. 趋势变化
    """
    suggestions = []
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    conn = get_connection()

    # ========================================
    # 维度1: 整体健康度检查
    # ========================================
    stats = get_overview_statistics()

    # 检查各活动参与率
    for table_key, activity_info in stats['activities'].items():
        total_records = activity_info['count']
        if total_records == 0 and table_key != 'study_tours':  # 游学非常规活动
            # 检查有哪些表完全没数据
            pass  # 先跳过，等有数据后再分析

    # ========================================
    # 维度2: 分层结构分析
    # ========================================
    layer_stats = stats['layer_stats']
    at_risk_pct = layer_stats['percentages'].get('at_risk', 0) + layer_stats['percentages'].get('dormant', 0)
    core_pct = layer_stats['percentages'].get('core', 0)

    # 流失风险过高预警
    if at_risk_pct > 30 and layer_stats['total'] > 5:
        suggestions.append({
            'generated_date': today_str,
            'analysis_dimension': '分层结构',
            'member_id': None,
            'suggestion_type': 'system',
            'title': '流失风险学员占比过高',
            'content': f'当前流失风险+待激活学员占比达 {at_risk_pct}%，建议制定全塾层面的激活计划，重点关注分层结构优化。',
            'priority': 'high',
        })

    # 核心层占比较低
    if core_pct < 15 and layer_stats['total'] > 5:
        suggestions.append({
            'generated_date': today_str,
            'analysis_dimension': '分层结构',
            'member_id': None,
            'suggestion_type': 'system',
            'title': '核心层占比偏低，需加大培养力度',
            'content': f"当前核心层学员仅占 {core_pct}%，建议加大对潜力学员的培养，提供更多成长机会，扩大核心骨干队伍。",
            'priority': 'medium',
        })

    # ========================================
    # 维度3: 分中心对比分析
    # ========================================
    center_analysis = get_group_analysis('center')
    if center_analysis:
        # 找出最佳和最差的分中心
        sorted_centers = sorted(center_analysis.items(), key=lambda x: x[1]['avg_score'], reverse=True)
        if len(sorted_centers) >= 2:
            best_center = sorted_centers[0]
            worst_center = sorted_centers[-1]

            # 最差的分中心给出建议
            if worst_center[1]['avg_score'] < 50:
                suggestions.append({
                    'generated_date': today_str,
                    'analysis_dimension': '分中心对比',
                    'member_id': None,
                    'suggestion_type': 'group',
                    'title': f"📉 {worst_center[0]} 综合评分偏低",
                    'content': f"{worst_center[0]} 平均评分 {worst_center[1]['avg_score']} 分，为全塾最低。建议向最佳分中心 {best_center[0]}（平均{best_center[1]['avg_score']}分）学习经验，安排跨中心交流。",
                    'priority': 'high',
                })

    # ========================================
    # 维度4: 学员个体分析
    # ========================================
    all_scores = calculate_all_members_scores()

    # 找出流失风险学员（dormant/at_risk）
    at_risk_members = [s for s in all_scores if s['layer'] in ['dormant', 'at_risk']]
    for s in at_risk_members[:5]:  # 最多5条个体建议
        # 检查连续未参与天数
        conn2 = get_connection()
        cur = conn2.cursor()
        # 查找最近一次参与记录
        cur.execute("""
            SELECT MAX(session_date) as last_date FROM (
                SELECT session_date FROM group_sessions WHERE member_id=?
                UNION
                SELECT session_date FROM class_sessions WHERE member_id=?
                UNION
                SELECT course_date FROM courses WHERE member_id=?
                UNION
                SELECT meeting_date FROM report_meetings WHERE member_id=?
                UNION
                SELECT tour_date FROM study_tours WHERE member_id=?
                UNION
                SELECT checkin_date FROM reading_checkins WHERE member_id=?
                UNION
                SELECT share_date FROM reading_shares WHERE member_id=?
            )
        """, tuple([s['member_id']] * 7))
        row = cur.fetchone()
        conn2.close()

        if row and row[0]:
            last_date = datetime.strptime(row[0], '%Y-%m-%d')
            days_since = (now - last_date).days
            if days_since > 60:
                suggestions.append({
                    'generated_date': today_str,
                    'analysis_dimension': '学员活跃度',
                    'member_id': s['member_id'],
                    'suggestion_type': 'individual',
                    'title': f"🛑 {s['name']} 已 {days_since} 天未参与活动",
                    'content': f"学员 {s['name']} 已连续 {days_since} 天未参与任何活动，当前为{s['layer_label']}。建议立即安排专人联系慰问。",
                    'priority': 'high',
                })

    # 找出表现突出的学员（core层 + 趋势上升）
    top_members = sorted(
        [s for s in all_scores if s['layer'] == 'core' and s['dimensions']['trend']['score'] > s['dimensions']['trend']['max'] * 0.6],
        key=lambda x: x['total_score'], reverse=True
    )
    for s in top_members[:3]:
        suggestions.append({
            'generated_date': today_str,
            'analysis_dimension': '学员表现',
            'member_id': s['member_id'],
            'suggestion_type': 'individual',
            'title': f"🏆 {s['name']} 本月表现优异",
            'content': f"学员 {s['name']} 综合评分 {s['total_score']} 分（{s['layer_label']}），且近期趋势持续上升。建议给予更多展示舞台，发挥榜样作用。",
            'priority': 'low',
        })

    # 找出有薄弱维度的学员
    for s in all_scores[:10]:  # 前10名检查
        weak = get_weak_dimensions(s)
        for w in weak:
            if w['name'] == 'reading':
                suggestions.append({
                    'generated_date': today_str,
                    'analysis_dimension': '阅读投入',
                    'member_id': s['member_id'],
                    'suggestion_type': 'individual',
                    'title': f"📚 {s['name']} 阅读维度待提升",
                    'content': f"学员 {s['name']} 阅读投入度得分较低（{w['score']}/{w['max']}），建议推荐合适书籍，邀请加入读书打卡群。",
                    'priority': 'medium',
                })
            elif w['name'] == 'diversity':
                suggestions.append({
                    'generated_date': today_str,
                    'analysis_dimension': '参与广度',
                    'member_id': s['member_id'],
                    'suggestion_type': 'individual',
                    'title': f"🎯 {s['name']} 参与类型较单一",
                    'content': f"学员 {s['name']} 参与活动类型较少，建议鼓励参加报告会、游学等多样化活动，丰富塾生体验。",
                    'priority': 'medium',
                })
            break  # 每人只生成一条建议

    # ========================================
    # 维度5: 特定异常检测
    # ========================================

    # 小组学习会出勤率异常
    conn3 = get_connection()
    cur = conn3.cursor()
    cur.execute("""
        SELECT strftime('%Y-%m', session_date) as month,
               COUNT(*) as total,
               SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
        FROM group_sessions
        WHERE session_date >= date('now', '-3 months')
        GROUP BY month
        ORDER BY month
    """)
    monthly_group = [dict(r) for r in cur.fetchall()]
    for m in monthly_group:
        rate = round(m['present'] / m['total'] * 100, 1) if m['total'] > 0 else 0
        if rate < 60 and m['total'] >= 10:
            suggestions.append({
                'generated_date': today_str,
                'analysis_dimension': '活动出勤',
                'member_id': None,
                'suggestion_type': 'system',
                'title': f"📅 {m['month']} 小组学习会出勤率偏低",
                'content': f"{m['month']} 小组学习会整体出勤率仅 {rate}%（参与{m['total']}人次），建议核查原因，优化学习会时间安排。",
                'priority': 'high',
            })

    conn3.close()

    # 保存建议到数据库
    for sg in suggestions:
        execute_insert('suggestions_log', sg)

    return suggestions


def get_recent_suggestions(days: int = 30) -> List[Dict]:
    """获取近期的运营建议"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM suggestions_log
        WHERE generated_date >= ?
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            generated_date DESC
    """, (cutoff,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_suggestion_summary() -> Dict:
    """获取建议汇总统计"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM suggestions_log")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT priority, COUNT(*) as count
        FROM suggestions_log
        GROUP BY priority
    """)
    by_priority = {dict(r)['priority']: dict(r)['count'] for r in cur.fetchall()}

    cur.execute("""
        SELECT suggestion_type, COUNT(*) as count
        FROM suggestions_log
        GROUP BY suggestion_type
    """)
    by_type = {dict(r)['suggestion_type']: dict(r)['count'] for r in cur.fetchall()}

    cur.execute("""
        SELECT is_adopted, COUNT(*) as count
        FROM suggestions_log
        GROUP BY is_adopted
    """)
    adoption = {dict(r)['is_adopted']: dict(r)['count'] for r in cur.fetchall()}

    conn.close()

    return {
        'total': total,
        'by_priority': by_priority,
        'by_type': by_type,
        'adoption_rate': round(adoption.get(1, 0) / total * 100, 1) if total > 0 else 0,
    }


if __name__ == "__main__":
    from database import init_database
    init_database()
    suggestions = generate_suggestions()
    print(f"生成了 {len(suggestions)} 条建议")
    for s in suggestions:
        print(f"[{s['priority']}] {s['title']}")
