"""
活动分析页面 - 各类活动参与情况分析
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database import table_to_df, get_connection, execute_query
from analysis_engine import get_activity_trends, get_group_analysis, get_cross_analysis


ACTIVITY_LABELS = {
    'group_sessions': '小组学习会',
    'class_sessions': '班级学习会',
    'courses': '课程',
    'report_meetings': '报告会',
    'study_tours': '游学',
    'reading_checkins': '读书打卡',
    'reading_shares': '读书分享',
}

ACTIVITY_DATE_COLS = {
    'group_sessions': 'session_date',
    'class_sessions': 'session_date',
    'courses': 'course_date',
    'report_meetings': 'meeting_date',
    'study_tours': 'tour_date',
    'reading_checkins': 'checkin_date',
    'reading_shares': 'share_date',
}


def render():
    st.title("📅 活动分析")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 活动概览", "🔄 交叉分析", "📈 趋势对比"])

    # ================================================================
    # Tab 1: 活动概览
    # ================================================================
    with tab1:
        st.subheader("各活动参与率对比")

        conn = get_connection()
        cur = conn.cursor()

        # 有 attendance 列的表
        attendance_tables = ['group_sessions', 'class_sessions', 'courses', 'report_meetings']
        # 无 attendance 列的表（记录即表示参与）
        auto_present_tables = ['study_tours', 'reading_checkins', 'reading_shares']

        activity_stats = []
        for table_key, label in ACTIVITY_LABELS.items():
            date_col = ACTIVITY_DATE_COLS[table_key]
            if table_key in attendance_tables:
                cur.execute(f"""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present,
                           COUNT(DISTINCT member_id) as unique_members
                    FROM {table_key}
                """)
            else:
                cur.execute(f"""
                    SELECT COUNT(*) as total,
                           COUNT(*) as present,
                           COUNT(DISTINCT member_id) as unique_members
                    FROM {table_key}
                """)
            row = dict(cur.fetchone())
            if row['total'] > 0:
                rate = round(row['present'] / row['total'] * 100, 1)
            else:
                rate = 0
            activity_stats.append({
                '活动类型': label,
                '总参与人次': row['total'],
                '出勤人次': row['present'],
                '参与率': rate,
                '参与学员数': row['unique_members'],
            })

        conn.close()

        if activity_stats and any(a['总参与人次'] > 0 for a in activity_stats):
            df = pd.DataFrame(activity_stats)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    df, x="活动类型", y="参与率",
                    color="活动类型", text="参与率",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig.update_layout(showlegend=False, height=400,
                                  yaxis_title="参与率(%)")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    df, x="活动类型", y="参与学员数",
                    color="活动类型", text="参与学员数",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig.update_layout(showlegend=False, height=400,
                                  yaxis_title="参与学员数")
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无活动数据，请先导入活动记录")

        # ---- 按活动类型查看明细 ----
        st.markdown("---")
        st.subheader("活动明细查看")

        selected_activity = st.selectbox(
            "选择活动类型查看明细",
            options=list(ACTIVITY_LABELS.keys()),
            format_func=lambda x: ACTIVITY_LABELS[x],
        )

        if selected_activity:
            df = table_to_df(selected_activity, "", ())
            if not df.empty:
                # 如果有关联学员ID，补上姓名
                if 'member_id' in df.columns:
                    members_df = table_to_df('members', '', ())
                    member_map = dict(zip(members_df['id'], members_df['name']))
                    df['学员姓名'] = df['member_id'].map(member_map).fillna('未知')

                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"共 {len(df)} 条记录")
            else:
                st.info(f"{ACTIVITY_LABELS[selected_activity]} 暂无数据")

    # ================================================================
    # Tab 2: 交叉分析
    # ================================================================
    with tab2:
        st.subheader("🔄 多维交叉分析")

        dim_options = {
            'center': '分中心',
            'class_name': '班级',
            'layer': '分层',
            'company_name': '公司',
        }

        col1, col2 = st.columns(2)
        with col1:
            dim1 = st.selectbox("维度一", options=list(dim_options.keys()),
                                format_func=lambda x: dim_options[x], key='dim1')
        with col2:
            dim2 = st.selectbox("维度二", options=list(dim_options.keys()),
                                format_func=lambda x: dim_options[x], key='dim2')

        if dim1 and dim2:
            if dim1 == dim2:
                st.warning("请选择两个不同的维度进行交叉分析")
            else:
                cross = get_cross_analysis(dim1, dim2)
                if cross:
                    # 转为 DataFrame
                    rows = []
                    for d1_val, sub in cross.items():
                        for d2_val, data in sub.items():
                            rows.append({
                                dim_options[dim1]: d1_val,
                                dim_options[dim2]: d2_val,
                                "学员数": data['count'],
                                "平均评分": data['avg_score'],
                            })
                    cross_df = pd.DataFrame(rows)

                    # 热力图
                    pivot = cross_df.pivot_table(
                        index=dim_options[dim1],
                        columns=dim_options[dim2],
                        values="平均评分",
                        aggfunc='first',
                    ).fillna(0)

                    fig = px.imshow(
                        pivot,
                        text_auto='.1f',
                        color_continuous_scale='RdYlGn',
                        aspect='auto',
                        height=max(400, len(pivot) * 40),
                    )
                    fig.update_layout(title=f"{dim_options[dim1]} × {dim_options[dim2]} 平均评分热力图")
                    st.plotly_chart(fig, use_container_width=True)

                    # 详细表格
                    st.markdown("---")
                    st.dataframe(cross_df.sort_values("平均评分", ascending=False),
                                 use_container_width=True, hide_index=True)
                else:
                    st.info("暂无交叉分析数据")

        # ---- 分中心 vs 分层交叉 ----
        st.markdown("---")
        st.subheader("📊 分中心×分层 分布矩阵")

        layer_cross = get_cross_analysis('center', 'layer')
        if layer_cross:
            layer_rows = []
            for center, sub in layer_cross.items():
                for layer, data in sub.items():
                    layer_rows.append({
                        "分中心": center,
                        "分层": LAYER_MAP.get(layer, {}).get('label', layer),
                        "人数": data['count'],
                    })
            layer_df = pd.DataFrame(layer_rows)
            if not layer_df.empty:
                fig = px.bar(
                    layer_df, x="分中心", y="人数", color="分层",
                    barmode="stack",
                    color_discrete_map={
                        LAYER_MAP['core']['label']: '#2ecc71',
                        LAYER_MAP['stable']['label']: '#3498db',
                        LAYER_MAP['potential']['label']: '#f39c12',
                        LAYER_MAP['at_risk']['label']: '#e67e22',
                        LAYER_MAP['dormant']['label']: '#e74c3c',
                    },
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

    # ================================================================
    # Tab 3: 趋势对比
    # ================================================================
    with tab3:
        st.subheader("📈 各活动月度趋势对比")

        trends = get_activity_trends(12)

        # 选择要对比的活动
        st.markdown("#### 选择要对比的活动类型")
        selected_tables = []
        cols = st.columns(4)
        for i, (table_key, tdata) in enumerate(trends['trends'].items()):
            with cols[i % 4]:
                if st.checkbox(tdata['label'], value=True, key=f"trend_{table_key}"):
                    selected_tables.append(table_key)

        if selected_tables:
            all_data = []
            for table_key in selected_tables:
                tdata = trends['trends'][table_key]
                for d in tdata['data']:
                    all_data.append({
                        '月份': d['month'],
                        '活动类型': tdata['label'],
                        '参与次数': d['count'],
                    })

            if all_data:
                trend_df = pd.DataFrame(all_data)
                fig = px.line(
                    trend_df, x="月份", y="参与次数", color="活动类型",
                    markers=True,
                )
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("所选活动暂无月度数据")

            # 年度累计对比
            st.markdown("---")
            st.subheader("📊 年度累计对比")
            if all_data:
                yearly = trend_df.groupby('活动类型')['参与次数'].sum().reset_index()
                fig = px.bar(
                    yearly, x="活动类型", y="参与次数",
                    color="活动类型", text="参与次数",
                )
                fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("请至少选择一个活动类型")


from utils.stratification import LAYER_MAP

if __name__ == "__main__":
    render()
