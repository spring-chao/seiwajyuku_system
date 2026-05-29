"""
学员分析页面 - 单学员全维度画像 + 学员列表分析
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from database import table_to_df, execute_query, get_connection
from analysis_engine import get_member_full_analysis, get_rankings
from utils.stratification import calculate_all_members_scores, LAYER_MAP


def render():
    st.title("👤 学员分析")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🔍 学员画像", "🏆 排行榜", "📋 学员列表"])

    # ================================================================
    # Tab 1: 学员画像
    # ================================================================
    with tab1:
        members = execute_query(
            "SELECT id, name, class_name, center FROM members WHERE status='active' ORDER BY name"
        )

        if not members:
            st.info("暂无学员数据，请先在数据导入页面导入学员信息")
            return

        member_options = {m['name']: m['id'] for m in members}

        col1, col2 = st.columns([3, 1])
        with col1:
            selected_name = st.selectbox(
                "选择学员", options=list(member_options.keys()),
                key="member_select"
            )
        with col2:
            st.markdown("")
            st.markdown("")

        if selected_name:
            member_id = member_options[selected_name]
            analysis = get_member_full_analysis(member_id)

            if not analysis:
                st.error("未找到该学员数据")
                return

            member = analysis['member']
            score = analysis['score']
            weak_dims = analysis['weak_dimensions']

            # ---- 学员信息卡 ----
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"**姓名**: {member['name']}")
                st.markdown(f"**手机**: {member['phone'] or '-'}")
            with col2:
                st.markdown(f"**班级**: {member['class_name'] or '-'}")
                st.markdown(f"**分中心**: {member['center'] or '-'}")
            with col3:
                st.markdown(f"**公司**: {member['company_name'] or '-'}")
                st.markdown(f"**职位**: {member['position'] or '-'}")
            with col4:
                date_val = member['join_date'] or '-'
                if date_val != '-' and 'T' in str(date_val):
                    date_val = str(date_val).split('T')[0]
                st.markdown(f"**入塾日期**: {date_val}")
                st.markdown(f"**推荐人**: {member['referrer'] or '-'}")

            st.markdown("---")

            # ---- 评分雷达图 ----
            col1, col2 = st.columns([2, 2])

            with col1:
                st.subheader(f"📊 综合评分: {score['total_score']} 分")
                st.markdown(f"**分层**: {score['layer_label']}")
                st.markdown(f"**说明**: {score['layer_desc']}")

                # 雷达图
                dims = score['dimensions']
                fig = go.Figure(data=go.Scatterpolar(
                    r=[dims[d]['score'] for d in dims],
                    theta=[dims[d]['label'] for d in dims],
                    fill='toself',
                    line_color='#e74c3c',
                ))
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, max(dims[d]['max'] for d in dims)]
                        )
                    ),
                    height=350,
                    showlegend=False,
                )
                st.plotly_chart(fig, width='stretch')

            with col2:
                st.subheader("📈 各维度详情")
                dim_df = pd.DataFrame([
                    {
                        "维度": dim_data['label'],
                        "得分": dim_data['score'],
                        "满分": dim_data['max'],
                        "得分率": f"{round(dim_data['score']/dim_data['max']*100, 1)}%",
                    }
                    for dim_name, dim_data in score['dimensions'].items()
                ])
                st.dataframe(dim_df, width='stretch', hide_index=True)

                # 薄弱维度预警
                if weak_dims:
                    st.markdown("#### ⚠️ 待提升维度")
                    for w in weak_dims:
                        st.warning(f"**{w['label']}**: {w['score']}/{w['max']} ({w['ratio']}%)")
                        st.caption(w['description'])

            st.markdown("---")

            # ---- 月度参与趋势 ----
            st.subheader("📅 各活动月度参与趋势")
            has_activity_data = False
            for table_key, rows in analysis['participation'].items():
                if rows:
                    has_activity_data = True
                    df = pd.DataFrame(rows)
                    df['present'] = pd.to_numeric(df['present'], errors='coerce').fillna(0)
                    df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0)
                    df['出勤率'] = round(df['present'] / df['total'] * 100, 1)

                    label_map = {
                        'group_sessions': '小组学习会',
                        'class_sessions': '班级学习会',
                        'courses': '课程',
                        'report_meetings': '报告会',
                    }

                    fig = px.line(
                        df, x="month", y="出勤率",
                        markers=True,
                        labels={"month": "月份", "出勤率": "出勤率(%)"},
                        title=label_map.get(table_key, table_key),
                    )
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, width='stretch')

            if not has_activity_data:
                st.info("暂无该学员的活动参与记录")

            # ---- 读书打卡日历 ----
            if analysis['checkins']:
                st.markdown("---")
                st.subheader("📚 读书打卡记录")
                checkin_df = pd.DataFrame(analysis['checkins'])
                if not checkin_df.empty:
                    st.dataframe(checkin_df, width='stretch', hide_index=True)

            # ---- 分享记录 ----
            if analysis['shares']:
                st.subheader("🎤 读书分享记录")
                share_df = pd.DataFrame(analysis['shares'])
                if not share_df.empty:
                    st.dataframe(share_df, width='stretch', hide_index=True)

            # ---- 游学记录 ----
            if analysis['tours']:
                st.subheader("✈️ 游学记录")
                tour_df = pd.DataFrame(analysis['tours'])
                if not tour_df.empty:
                    st.dataframe(tour_df, width='stretch', hide_index=True)

    # ================================================================
    # Tab 2: 排行榜
    # ================================================================
    with tab2:
        st.subheader("🏆 综合排行榜")
        rankings = get_rankings(30)

        # 综合排行
        top_df = pd.DataFrame([
            {
                "排名": i + 1,
                "姓名": r['name'],
                "综合评分": r['total_score'],
                "分层": r['layer_label'],
            }
            for i, r in enumerate(rankings['综合排行'])
        ])
        st.dataframe(top_df, width='stretch', hide_index=True)

        # 出勤率排行
        st.markdown("---")
        st.subheader("📊 出勤率排行")
        att_df = pd.DataFrame([
            {
                "排名": i + 1,
                "姓名": r['name'],
                "出勤率": f"{r['attendance_rate']}%",
                "参与活动数": r['present'],
                "总活动数": r['total_activities'],
                "分层": r['layer'],
            }
            for i, r in enumerate(rankings['attendance_ranking'][:20])
        ])
        st.dataframe(att_df, width='stretch', hide_index=True)

        # 各维度排行
        st.markdown("---")
        st.subheader("📈 各维度排行")
        dim_tabs = st.tabs(list(rankings['dimension_rankings'].keys()))
        for i, (dim_name, dim_list) in enumerate(rankings['dimension_rankings'].items()):
            with dim_tabs[i]:
                dim_df = pd.DataFrame([
                    {"排名": j + 1, "姓名": r['name'], "得分": r['score'], "分层": r.get('layer', '-')}
                    for j, r in enumerate(dim_list)
                ])
                st.dataframe(dim_df, width='stretch', hide_index=True)

    # ================================================================
    # Tab 3: 学员列表
    # ================================================================
    with tab3:
        st.subheader("📋 全体学员列表")
        all_scores = calculate_all_members_scores()

        if all_scores:
            list_df = pd.DataFrame([
                {
                    "姓名": s['name'],
                    "综合评分": s['total_score'],
                    "分层": s['layer_label'],
                    "班级": s.get('class_name', ''),
                    "分中心": s.get('center', ''),
                    "参与度": f"{s['dimensions']['participation']['score']}/{s['dimensions']['participation']['max']}",
                    "阅读": f"{s['dimensions']['reading']['score']}/{s['dimensions']['reading']['max']}",
                    "趋势": f"{s['dimensions']['trend']['score']}/{s['dimensions']['trend']['max']}",
                    "广度": f"{s['dimensions']['diversity']['score']}/{s['dimensions']['diversity']['max']}",
                }
                for s in all_scores
            ]).sort_values("综合评分", ascending=False)

            st.dataframe(list_df, width='stretch', hide_index=True)

            # 分层筛选
            st.markdown("---")
            st.subheader("🔎 按分层筛选")
            layer_filter = st.selectbox(
                "选择分层", options=['全部'] + [LAYER_MAP[k]['label'] for k in LAYER_MAP]
            )
            if layer_filter != '全部':
                # 找到对应的 layer key
                layer_key = next(k for k, v in LAYER_MAP.items() if v['label'] == layer_filter)
                filtered = [s for s in all_scores if s['layer'] == layer_key]
                filtered_df = pd.DataFrame([
                    {"姓名": s['name'], "综合评分": s['total_score'],
                     "班级": s.get('class_name', ''), "分中心": s.get('center', '')}
                    for s in filtered
                ])
                st.dataframe(filtered_df, width='stretch', hide_index=True)
                if len(filtered) > 0:
                    st.info(f"共 {len(filtered)} 名学员属于 {layer_filter}")
        else:
            st.info("暂无学员评分数据，请先导入学员信息和活动数据")


if __name__ == "__main__":
    render()
