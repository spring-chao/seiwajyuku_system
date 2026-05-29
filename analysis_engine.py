"""
盛和塾运营管理系统 - 分析引擎
提供各类数据分析和交叉分析功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

from database import get_connection, execute_query, table_to_df
from utils.stratification import (
    calculate_member_score, calculate_all_members_scores,
    get_layer_statistics, get_weak_dimensions, LAYER_MAP
)


# ============================================================
# 1. 整体运营统计
# ============================================================

def get_overview_statistics() -> Dict:
    """获取整体运营统计"""
    conn = get_connection()
    cur = conn.cursor()

    # 学员总数
    cur.execute("SELECT COUNT(*) FROM members WHERE status='active'")
    active_members = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM members")
    total_members = cur.fetchone()[0]

    # 分中心数
    cur.execute("SELECT COUNT(DISTINCT center) FROM members WHERE center IS NOT NULL AND center!=''")
    center_count = cur.fetchone()[0]

    # 班级数
    cur.execute("SELECT COUNT(DISTINCT class_name) FROM members WHERE class_name IS NOT NULL AND class_name!=''")
    class_count = cur.fetchone()[0]

    # 各活动总记录数
    activity_tables = {
        'group_sessions': '小组学习会',
        'class_sessions': '班级学习会',
        'courses': '课程',
        'report_meetings': '报告会',
        'study_tours': '游学',
        'reading_checkins': '读书打卡',
        'reading_shares': '读书分享',
    }

    activities = {}
    total_activities = 0
    for table, label in activity_tables.items():
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(DISTINCT member_id) FROM {table}")
        member_count = cur.fetchone()[0]
        activities[table] = {'label': label, 'count': count, 'member_count': member_count}
        total_activities += count

    # 分层统计
    layer_stats = get_layer_statistics()

    conn.close()

    return {
        'total_members': total_members,
        'active_members': active_members,
        'center_count': center_count,
        'class_count': class_count,
        'activities': activities,
        'total_activities': total_activities,
        'layer_stats': layer_stats,
    }


# ============================================================
# 2. 单学员全维度分析
# ============================================================

def get_member_full_analysis(member_id: int) -> Dict:
    """获取学员全维度分析"""
    # 基本信息
    member = execute_query(
        "SELECT * FROM members WHERE id=?", (member_id,)
    )
    if not member:
        return {}
    member = member[0]

    # 分层评分
    score = calculate_member_score(member_id)

    # 薄弱维度
    weak_dims = get_weak_dimensions(score)

    # 参与详情
    participation = {}
    conn = get_connection()
    cur = conn.cursor()

    # 各活动的月度趋势
    table_configs = [
        ('group_sessions', 'session_date'),
        ('class_sessions', 'session_date'),
        ('courses', 'course_date'),
        ('report_meetings', 'meeting_date'),
    ]
    for table, date_col in table_configs:
        cur.execute(f"""
            SELECT strftime('%Y-%m', {date_col}) as month,
                   COUNT(*) as total,
                   SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
            FROM {table}
            WHERE member_id=?
            GROUP BY month
            ORDER BY month
        """, (member_id,))
        participation[table] = [dict(r) for r in cur.fetchall()]

    # 读书打卡日历
    cur.execute("""
        SELECT checkin_date, book_name, pages_read
        FROM reading_checkins
        WHERE member_id=?
        ORDER BY checkin_date DESC
        LIMIT 100
    """, (member_id,))
    checkins = [dict(r) for r in cur.fetchall()]

    # 分享记录
    cur.execute("""
        SELECT share_date, book_name, share_type, quality_score
        FROM reading_shares
        WHERE member_id=?
        ORDER BY share_date DESC
        LIMIT 50
    """, (member_id,))
    shares = [dict(r) for r in cur.fetchall()]

    # 游学记录
    cur.execute("""
        SELECT destination, tour_date, duration_days, harvest_score
        FROM study_tours
        WHERE member_id=?
        ORDER BY tour_date DESC
    """, (member_id,))
    tours = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        'member': member,
        'score': score,
        'weak_dimensions': weak_dims,
        'participation': participation,
        'checkins': checkins,
        'shares': shares,
        'tours': tours,
    }


# ============================================================
# 3. 按分组分析
# ============================================================

def get_group_analysis(group_by: str = 'center') -> Dict:
    """
    按分中心/班级/推荐人分组分析参与情况
    """
    scores = calculate_all_members_scores()

    # 按指定维度分组
    groups = {}
    for s in scores:
        key = s.get(group_by, '未知')
        if key not in groups:
            groups[key] = {'members': [], 'count': 0, 'scores': []}
        groups[key]['members'].append(s['name'])
        groups[key]['count'] += 1
        groups[key]['scores'].append(s['total_score'])

    # 汇总统计
    summary = {}
    for key, data in groups.items():
        scores_arr = data['scores']
        summary[key] = {
            'count': data['count'],
            'avg_score': round(np.mean(scores_arr), 1) if scores_arr else 0,
            'max_score': max(scores_arr) if scores_arr else 0,
            'min_score': min(scores_arr) if scores_arr else 0,
            'std_score': round(np.std(scores_arr), 1) if len(scores_arr) > 1 else 0,
            'layer_distribution': _get_layer_dist(data['members']),
        }

    return summary


def _get_layer_dist(member_names: List[str]) -> Dict:
    """获取一组学员的分层分布"""
    scores = calculate_all_members_scores()
    filtered = [s for s in scores if s['name'] in member_names]
    dist = {k: 0 for k in LAYER_MAP}
    for s in filtered:
        dist[s['layer']] += 1
    return dist


# ============================================================
# 4. 交叉分析
# ============================================================

def get_cross_analysis(dim1: str, dim2: str) -> Dict:
    """
    交叉分析: 如 班级×参与率, 分中心×分层等
    """
    scores = calculate_all_members_scores()

    # 构建二维矩阵
    matrix = {}
    for s in scores:
        d1_val = str(s.get(dim1, '未知'))
        d2_val = str(s.get(dim2, '未知'))

        if d1_val not in matrix:
            matrix[d1_val] = {}
        if d2_val not in matrix[d1_val]:
            matrix[d1_val][d2_val] = {'count': 0, 'total_score': 0}

        matrix[d1_val][d2_val]['count'] += 1
        matrix[d1_val][d2_val]['total_score'] += s['total_score']

    # 计算平均值
    result = {}
    for d1, sub in matrix.items():
        result[d1] = {}
        for d2, data in sub.items():
            result[d1][d2] = {
                'count': data['count'],
                'avg_score': round(data['total_score'] / data['count'], 1)
            }

    return result


# ============================================================
# 5. 趋势分析
# ============================================================

def get_activity_trends(months: int = 12) -> Dict:
    """
    获取各类活动的月度趋势
    """
    conn = get_connection()
    cur = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=30 * months)).strftime('%Y-%m-%d')

    tables = [
        ('group_sessions', '小组学习会'),
        ('class_sessions', '班级学习会'),
        ('courses', '课程'),
        ('report_meetings', '报告会'),
        ('study_tours', '游学'),
        ('reading_checkins', '读书打卡'),
        ('reading_shares', '读书分享'),
    ]

    trends = {}
    for table, label in tables:
        date_col = 'session_date'
        if table == 'reading_checkins':
            date_col = 'checkin_date'
        elif table == 'reading_shares':
            date_col = 'share_date'
        elif table == 'study_tours':
            date_col = 'tour_date'
        elif table == 'courses':
            date_col = 'course_date'
        elif table == 'report_meetings':
            date_col = 'meeting_date'

        cur.execute(f"""
            SELECT strftime('%Y-%m', {date_col}) as month,
                   COUNT(*) as count
            FROM {table}
            WHERE {date_col} >= ?
            GROUP BY month
            ORDER BY month
        """, (cutoff,))

        rows = [dict(r) for r in cur.fetchall()]
        trends[table] = {
            'label': label,
            'data': rows,
        }

    # 整体月度参与人数
    cur.execute(f"""
        SELECT strftime('%Y-%m', session_date) as month,
               COUNT(DISTINCT member_id) as members
        FROM group_sessions
        WHERE session_date >= ?
        GROUP BY month
        ORDER BY month
    """, (cutoff,))
    overall_monthly = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        'trends': trends,
        'overall_monthly': overall_monthly,
    }


# ============================================================
# 6. 排行榜
# ============================================================

def get_rankings(top_n: int = 20) -> Dict:
    """
    获取各类排行
    """
    scores = calculate_all_members_scores()

    # 综合评分排行
    by_score = sorted(scores, key=lambda x: x['total_score'], reverse=True)[:top_n]
    # 添加 'score' 别名，便于统一渲染
    for s in by_score:
        s['score'] = s['total_score']

    # 各维度排行
    dimensions = ['participation', 'reading', 'trend', 'diversity']
    rankings = {'综合排行': by_score}

    for dim in dimensions:
        ranked = sorted(scores, key=lambda x: x['dimensions'][dim]['score'], reverse=True)[:top_n]
        rankings[f"{dim}排行"] = [
            {'name': r['name'], 'score': r['dimensions'][dim]['score'],
             'max': r['dimensions'][dim]['max'], 'layer': r['layer']}
            for r in ranked
        ]

    # 出勤率排行（有数据的学员）
    conn = get_connection()
    cur = conn.cursor()

    attendance_ranking = []
    for s in scores:
        cur.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
            FROM (
                SELECT attendance, session_date as d FROM group_sessions WHERE member_id=?
                UNION ALL
                SELECT attendance, session_date FROM class_sessions WHERE member_id=?
                UNION ALL
                SELECT attendance, course_date FROM courses WHERE member_id=?
                UNION ALL
                SELECT attendance, meeting_date FROM report_meetings WHERE member_id=?
            )
        """, (s['member_id'], s['member_id'], s['member_id'], s['member_id']))

        stats = dict(cur.fetchone())
        if stats['total'] > 0:
            rate = round(stats['present'] / stats['total'] * 100, 1)
            attendance_ranking.append({
                'name': s['name'],
                'total_activities': stats['total'],
                'present': stats['present'],
                'attendance_rate': rate,
                'layer': s['layer'],
            })

    attendance_ranking.sort(key=lambda x: x['attendance_rate'], reverse=True)

    conn.close()

    return {
        '综合排行': by_score,
        'attendance_ranking': attendance_ranking[:top_n],
        'dimension_rankings': rankings,
    }


# ============================================================
# 7. 班级/分中心对比
# ============================================================

def get_unit_comparison() -> Dict:
    """分中心和班级的横向对比"""
    center_analysis = get_group_analysis('center')
    class_analysis = get_group_analysis('class_name')

    return {
        'center': center_analysis,
        'class': class_analysis,
    }


if __name__ == "__main__":
    from database import init_database
    init_database()
    print(get_overview_statistics())
