"""
总览看板页面 - 盛和塾运营数据总览
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict

from database import table_to_df, get_connection
from analysis_engine import get_overview_statistics, get_activity_trends, get_unit_comparison
from utils.stratification import get_layer_statistics, LAYER_MAP


def render():
    st.set_page_config(page_title="盛和塾运营管理系统", page_icon="🏛️", layout="wide")
    st.title("🏛️ 盛和塾运营管理系统")
    st.markdown("---")

    # 获取统计数据
    stats = get_overview_statistics()

    # ---- 顶部指标卡 ----
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📋 学员总数", stats['active_members'],
                  f"共{stats['total_members']}人(含非活跃)")
    with col2:
        st.metric("🏢 分中心数", stats['center_count'])
    with col3:
        st.metric("📚 班级数", stats['class_count'])
    with col4:
        st.metric("📊 活动总记录", stats['total_activities'])
    with col5:
        layer_stats = stats['layer_stats']
        core_pct = layer_stats['percentages'].get('core', 0)
        st.metric("🌟 核心层占比", f"{core_pct}%")

    st.markdown("---")

    # ---- 第二行: 活动概况 + 分层分布 ----
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("📊 各活动数据量")
        activities_df = pd.DataFrame([
            {"活动类型": v['label'], "记录数": v['count']}
            for v in stats['activities'].values()
        ])
        fig = px.bar(
            activities_df, x="活动类型", y="记录数",
            color="活动类型", text="记录数",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader("🎯 学员分层分布")
        layer_stats = stats['layer_stats']
        layer_df = pd.DataFrame([
            {"分层": LAYER_MAP[k]['label'], "人数": v}
            for k, v in layer_stats['counts'].items()
        ])
        fig = px.pie(
            layer_df, values="人数", names="分层",
            color="分层",
            color_discrete_map={
                LAYER_MAP['core']['label']: '#2ecc71',
                LAYER_MAP['stable']['label']: '#3498db',
                LAYER_MAP['potential']['label']: '#f39c12',
                LAYER_MAP['at_risk']['label']: '#e67e22',
                LAYER_MAP['dormant']['label']: '#e74c3c',
            },
            hole=0.4,
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, width='stretch')

    st.markdown("---")

    # ---- 第三行: 月度趋势 + 分中心对比 ----
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 月度参与趋势")
        trends = get_activity_trends(6)

        if trends['overall_monthly']:
            trend_df = pd.DataFrame(trends['overall_monthly'])
            fig = px.line(
                trend_df, x="month", y="members",
                markers=True,
                labels={"month": "月份", "members": "参与人数"},
                color_discrete_sequence=['#e74c3c'],
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("暂无月度趋势数据，请先导入活动记录")

    with col2:
        st.subheader("🏢 分中心评分对比")
        comparison = get_unit_comparison()
        centers = comparison.get('center', {})
        if centers:
            center_df = pd.DataFrame([
                {"分中心": k, "平均评分": v['avg_score'], "学员数": v['count']}
                for k, v in centers.items()
            ]).sort_values("平均评分", ascending=True)

            fig = px.bar(
                center_df, x="平均评分", y="分中心",
                color="平均评分", text="平均评分",
                color_continuous_scale='RdYlGn',
                orientation='h',
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("暂无分中心数据")

    st.markdown("---")

    # ---- 第四行: 各活动类型趋势 ----
    st.subheader("📅 各类活动月度趋势")
    trends = get_activity_trends(12)
    if any(v['data'] for v in trends['trends'].values()):
        # 合并为 DataFrame
        all_trends = []
        for table_key, tdata in trends['trends'].items():
            for d in tdata['data']:
                all_trends.append({
                    '月份': d['month'],
                    '活动类型': tdata['label'],
                    '次数': d['count'],
                })
        if all_trends:
            trend_df = pd.DataFrame(all_trends)
            fig = px.line(
                trend_df, x="月份", y="次数", color="活动类型",
                markers=True,
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("暂无活动趋势数据，请先导入活动记录")

    # ---- 底部: 数据概览表 ----
    st.markdown("---")
    st.subheader("📋 数据导入概览")
    overview_df = pd.DataFrame([
        {"数据表": v['label'], "记录数": v['count'], "参与学员": v['member_count']}
        for k, v in stats['activities'].items()
    ])
    st.dataframe(overview_df, width='stretch', hide_index=True)

    # 最后导入记录
    conn = get_connection()
    recent_imports = pd.read_sql_query(
        "SELECT import_date, file_name, table_name, record_count, status FROM import_log ORDER BY import_date DESC LIMIT 5",
        conn
    )
    conn.close()
    if not recent_imports.empty:
        st.markdown("#### 最近导入记录")
        st.dataframe(recent_imports, width='stretch', hide_index=True)


if __name__ == "__main__":
    render()
