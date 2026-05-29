"""
综合洞察与建议页面 - 运营建议、智能分析报告
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from database import get_connection, execute_query, execute_update
from suggestions import generate_suggestions, get_recent_suggestions, get_suggestion_summary
from analysis_engine import get_overview_statistics, get_unit_comparison
from utils.stratification import get_layer_statistics, LAYER_MAP


def render():
    st.title("💡 综合洞察与建议")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🤖 智能建议", "📊 专题分析", "📈 趋势预警"])

    # ================================================================
    # Tab 1: 智能建议
    # ================================================================
    with tab1:
        st.subheader("🤖 智能运营建议")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("系统基于学员分层模型和各维度参与数据，自动生成个性化运营建议")
        with col2:
            if st.button("🔄 重新生成建议", use_container_width=True):
                with st.spinner("正在分析数据，生成建议..."):
                    suggestions = generate_suggestions()
                st.success(f"✅ 已生成 {len(suggestions)} 条新建议")
                st.rerun()

        # 建议汇总统计
        summary = get_suggestion_summary()
        if summary['total'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📋 建议总数", summary['total'])
            with col2:
                high = summary['by_priority'].get('high', 0)
                st.metric("🔴 高优先级", high)
            with col3:
                st.metric("✅ 已采纳", summary['by_priority'].get('medium', 0))
            with col4:
                st.metric("📈 采纳率", f"{summary['adoption_rate']}%")

            # 建议列表
            st.markdown("---")
            suggestions_list = get_recent_suggestions(90)

            if suggestions_list:
                for sg in suggestions_list:
                    priority_emoji = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢',
                    }.get(sg['priority'], '⚪')

                    type_label = {
                        'individual': '个人',
                        'group': '群体',
                        'system': '系统',
                    }.get(sg['suggestion_type'], '其他')

                    with st.container(border=True):
                        col1, col2 = st.columns([8, 2])
                        with col1:
                            st.markdown(f"{priority_emoji} **{sg['title']}**")
                            st.markdown(f"{sg['content']}")
                            st.caption(f"维度: {sg['analysis_dimension']} | 类型: {type_label} | {sg['generated_date']}")
                        with col2:
                            if sg['is_adopted'] == 0:
                                if st.button("✅ 采纳", key=f"adopt_{sg['id']}"):
                                    execute_update(
                                        'suggestions_log',
                                        {'is_adopted': 1, 'adopted_date': datetime.now().strftime('%Y-%m-%d')},
                                        'id=?', (sg['id'],)
                                    )
                                    st.success("已标记为采纳")
                                    st.rerun()
                            else:
                                st.markdown("✅ **已采纳**")
                                if sg['adopted_date']:
                                    st.caption(f"于 {sg['adopted_date']}")
            else:
                st.info('暂无建议，点击重新生成建议按钮生成')
        else:
            st.info('暂无建议数据，点击重新生成建议按钮生成第一条建议')

    # ================================================================
    # Tab 2: 专题分析
    # ================================================================
    with tab2:
        st.subheader("📊 专题分析报告")

        report_type = st.selectbox(
            "选择分析专题",
            options=[
                "学员分层结构分析",
                "分中心对比分析",
                "班级活跃度分析",
                "读书活动分析",
                "综合运营报告",
            ]
        )

        if report_type == "学员分层结构分析":
            render_layer_analysis()
        elif report_type == "分中心对比分析":
            render_center_comparison()
        elif report_type == "读书活动分析":
            render_reading_analysis()
        elif report_type == "综合运营报告":
            render_comprehensive_report()
        else:
            render_class_analysis()

    # ================================================================
    # Tab 3: 趋势预警
    # ================================================================
    with tab3:
        st.subheader("📈 趋势预警看板")

        conn = get_connection()
        cur = conn.cursor()

        # 1. 参与率持续下降预警
        st.markdown("#### 🔻 参与率下降预警")
        cur.execute("""
            SELECT strftime('%Y-%m', session_date) as month,
                   COUNT(DISTINCT member_id) as active_members,
                   COUNT(*) as total_sessions,
                   SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
            FROM group_sessions
            WHERE session_date >= date('now', '-6 months')
            GROUP BY month
            ORDER BY month
        """)
        monthly_data = [dict(r) for r in cur.fetchall()]

        if len(monthly_data) >= 2:
            rates = []
            for m in monthly_data:
                rate = round(m['present'] / m['total_sessions'] * 100, 1) if m['total_sessions'] > 0 else 0
                rates.append(rate)

            # 检查是否持续下降
            if rates[-1] < rates[0] * 0.8:
                st.warning(f"⚠️ 小组学习会参与率从 {rates[0]}% 下降至 {rates[-1]}%，降幅明显")
            elif rates[-1] < rates[0] * 0.9:
                st.info(f"📉 小组学习会参与率略有下降: {rates[0]}% → {rates[-1]}%")

            # 展示趋势
            trend_df = pd.DataFrame({
                '月份': [m['month'] for m in monthly_data],
                '参与率(%)': rates,
                '活跃学员': [m['active_members'] for m in monthly_data],
            })
            fig = px.line(trend_df, x='月份', y='参与率(%)', markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("数据不足6个月，无法分析趋势")

        # 2. 学员流失预警
        st.markdown("---")
        st.markdown("#### 🚨 学员流失预警")

        layer_stats = get_layer_statistics()
        at_risk_total = layer_stats['counts'].get('at_risk', 0) + layer_stats['counts'].get('dormant', 0)
        total = layer_stats['total']

        if total > 0:
            risk_rate = round(at_risk_total / total * 100, 1)
            if risk_rate > 30:
                st.error(f"🚨 高流失风险！{risk_rate}% 的学员(共{at_risk_total}人)处于待激活或流失风险状态")
            elif risk_rate > 15:
                st.warning(f"⚠️ {risk_rate}% 的学员需要关注激活({at_risk_total}人)")
            else:
                st.success(f"✅ 分层结构健康，仅 {risk_rate}% 学员处于流失风险({at_risk_total}人)")

            # 分层趋势
            st.markdown("#### 分层分布详情")
            layer_df = pd.DataFrame([
                {"分层": LAYER_MAP[k]['label'], "人数": v, "说明": LAYER_MAP[k]['desc']}
                for k, v in layer_stats['counts'].items()
            ])
            st.dataframe(layer_df, use_container_width=True, hide_index=True)

        # 3. 数据完整性检查
        st.markdown("---")
        st.markdown("#### 📋 数据完整性检查")

        tables_check = [
            ('members', '学员信息', True),
            ('group_sessions', '小组学习会', False),
            ('class_sessions', '班级学习会', False),
            ('courses', '课程记录', False),
            ('reading_checkins', '读书打卡', False),
        ]

        for table, label, required in tables_check:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            if count == 0:
                if required:
                    st.error(f"❌ {label}：无数据（必填）")
                else:
                    st.warning(f"⚠️ {label}：暂无数据")
            else:
                st.success(f"✅ {label}：{count} 条记录")

        conn.close()


# ================================================================
# 专题分析子函数
# ================================================================

def render_layer_analysis():
    """分层结构分析"""
    layer_stats = get_layer_statistics()

    st.markdown("#### 分层结构总览")
    col1, col2 = st.columns(2)
    with col1:
        layer_df = pd.DataFrame([
            {"分层": LAYER_MAP[k]['label'], "人数": v, "占比": f"{layer_stats['percentages'].get(k, 0)}%"}
            for k, v in layer_stats['counts'].items()
        ])
        st.dataframe(layer_df, use_container_width=True, hide_index=True)

    with col2:
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Pie(
            labels=[LAYER_MAP[k]['label'] for k in LAYER_MAP],
            values=[layer_stats['counts'].get(k, 0) for k in LAYER_MAP],
            hole=0.4,
            marker=dict(colors=['#2ecc71', '#3498db', '#f39c12', '#e67e22', '#e74c3c']),
        )])
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # 建议
    if layer_stats['total'] > 0:
        st.markdown("#### 分层优化建议")
        core_pct = layer_stats['percentages'].get('core', 0)
        dormant_pct = layer_stats['percentages'].get('dormant', 0)

        recommendations = []
        if core_pct < 15:
            recommendations.append('核心层占比偏低：建议增设骨干培养计划，鼓励潜力学员承担更多责任')
        if dormant_pct > 20:
            recommendations.append('流失风险学员过多：建议启动老学员回归计划，逐一联系了解情况')
        if layer_stats['counts'].get('potential', 0) > layer_stats['counts'].get('stable', 0):
            recommendations.append('潜力层学员充足：建议制定"潜力到核心"的成长路径')
        if not recommendations:
            recommendations.append("✅ 分层结构健康，继续保持")

        for rec in recommendations:
            st.info(rec)


def render_center_comparison():
    """分中心对比分析"""
    comparison = get_unit_comparison()
    centers = comparison.get('center', {})
    if not centers:
        st.info("暂无分中心数据")
        return

    center_df = pd.DataFrame([
        {"分中心": k, "学员数": v['count'], "平均评分": v['avg_score'],
         "最高分": v['max_score'], "最低分": v['min_score']}
        for k, v in centers.items()
    ])

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(center_df, x="分中心", y="平均评分", color="平均评分",
                     color_continuous_scale='RdYlGn', text="平均评分")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(center_df, x="学员数", y="平均评分", size="学员数",
                         text="分中心", color="平均评分",
                         color_continuous_scale='RdYlGn')
        fig.update_traces(textposition='top center')
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(center_df.sort_values("平均评分", ascending=False),
                 use_container_width=True, hide_index=True)


def render_reading_analysis():
    """读书活动分析"""
    conn = get_connection()
    cur = conn.cursor()

    st.markdown("#### 读书打卡统计")
    cur.execute("""
        SELECT COUNT(DISTINCT member_id) as readers,
               COUNT(*) as total_checkins,
               COUNT(DISTINCT book_name) as unique_books,
               AVG(pages_read) as avg_pages
        FROM reading_checkins
    """)
    stats = dict(cur.fetchone())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📖 打卡学员", stats['readers'] or 0)
    with col2:
        st.metric("📚 打卡次数", stats['total_checkins'] or 0)
    with col3:
        st.metric("📕 涉及书籍", stats['unique_books'] or 0)
    with col4:
        st.metric("📄 平均页数", round(stats['avg_pages'] or 0, 1))

    # 热门书籍
    st.markdown("#### 热门书籍 Top 10")
    cur.execute("""
        SELECT book_name, COUNT(*) as count, COUNT(DISTINCT member_id) as readers
        FROM reading_checkins
        WHERE book_name IS NOT NULL AND book_name != ''
        GROUP BY book_name
        ORDER BY count DESC
        LIMIT 10
    """)
    books = [dict(r) for r in cur.fetchall()]
    if books:
        book_df = pd.DataFrame(books)
        fig = px.bar(book_df, x="book_name", y="count", color="readers",
                     text="count", labels={"book_name": "书名", "count": "打卡次数", "readers": "读者数"})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # 分享统计
    st.markdown("---")
    st.markdown("#### 读书分享统计")
    cur.execute("""
        SELECT COUNT(DISTINCT member_id) as sharers,
               COUNT(*) as total_shares,
               AVG(quality_score) as avg_quality
        FROM reading_shares
    """)
    share_stats = dict(cur.fetchone())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎤 分享学员", share_stats['sharers'] or 0)
    with col2:
        st.metric("📝 分享次数", share_stats['total_shares'] or 0)
    with col3:
        st.metric("⭐ 平均质量评分", round(share_stats['avg_quality'] or 0, 1))

    conn.close()


def render_comprehensive_report():
    """综合运营报告"""
    stats = get_overview_statistics()
    st.markdown("#### 📋 综合运营报告")

    # 生成报告文本
    report_parts = []

    report_parts.append(f"### 📊 综合运营报告 ({datetime.now().strftime('%Y-%m-%d')})")
    report_parts.append("")
    report_parts.append("#### 一、基本情况")
    report_parts.append(f"- 活跃学员：{stats['active_members']} 人（共 {stats['total_members']} 人）")
    report_parts.append(f"- 分中心数：{stats['center_count']} 个")
    report_parts.append(f"- 班级数：{stats['class_count']} 个")
    report_parts.append("")

    report_parts.append("#### 二、活动数据")
    report_parts.append(f"- 活动总记录：{stats['total_activities']} 条")
    for table_key, info in stats['activities'].items():
        report_parts.append(f"- {info['label']}：{info['count']} 条")
    report_parts.append("")

    report_parts.append("#### 三、分层结构")
    layer_stats = stats['layer_stats']
    for k, v in layer_stats['counts'].items():
        pct = layer_stats['percentages'].get(k, 0)
        report_parts.append(f"- {LAYER_MAP[k]['label']}：{v} 人（{pct}%）")
    report_parts.append("")

    report_parts.append("#### 四、运营建议")
    suggestions = get_recent_suggestions(30)
    if suggestions:
        for sg in suggestions[:5]:
            report_parts.append(f"- [{sg['priority']}] {sg['title']}")
    else:
        report_parts.append("- 暂无建议")

    st.markdown("\n".join(report_parts))

    if st.button("📄 复制报告", use_container_width=False):
        st.toast("报告已生成，请手动复制")


def render_class_analysis():
    """班级活跃度分析"""
    comparison = get_unit_comparison()
    classes = comparison.get('class', {})
    if not classes:
        st.info("暂无班级数据")
        return

    class_df = pd.DataFrame([
        {"班级": k, "学员数": v['count'], "平均评分": v['avg_score']}
        for k, v in classes.items()
    ]).sort_values("平均评分", ascending=False)

    fig = px.bar(class_df, x="班级", y="平均评分", color="平均评分",
                 color_continuous_scale='RdYlGn', text="平均评分")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(class_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render()
