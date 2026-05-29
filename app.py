"""
盛和塾运营管理系统 - 主入口
Streamlit 多页面应用
"""

import streamlit as st
import sys
from pathlib import Path

# 确保能导入同级模块
sys.path.insert(0, str(Path(__file__).parent))

from database import init_database
from data_import import get_import_guide, IMPORT_TEMPLATES, COLUMN_ALIASES, import_excel
from suggestions import generate_suggestions
from datetime import datetime

# ---- 页面配置 ----
st.set_page_config(
    page_title="盛和塾运营管理系统",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 会话状态初始化 ----
if 'db_initialized' not in st.session_state:
    init_database()
    st.session_state.db_initialized = True
    # 首次启动时生成初始建议
    st.session_state.suggestions_generated = False


# ---- 侧边栏导航 ----
def main():
    st.sidebar.title("🏛️ 盛和塾运营管理")
    st.sidebar.markdown("---")

    # 主导航
    nav_options = {
        "📊 总览看板": "overview",
        "👤 学员分析": "member",
        "📅 活动分析": "activity",
        "💡 综合洞察": "insights",
        "📥 数据导入": "import",
    }

    # 初始化导航状态
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "overview"

    for label, page_id in nav_options.items():
        if st.sidebar.button(label, use_container_width=True,
                             type="primary" if st.session_state.current_page == page_id else "secondary"):
            st.session_state.current_page = page_id
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 系统信息")
    st.sidebar.caption("版本: 1.0.0")
    st.sidebar.caption("数据库: SQLite (本地)")

    # 系统快速操作
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚡ 快捷操作")

    if st.sidebar.button("🤖 生成运营建议", use_container_width=True):
        with st.spinner("正在分析数据，生成建议..."):
            count = len(generate_suggestions())
        st.sidebar.success(f"✅ 已生成 {count} 条建议")

    if st.sidebar.button("🔄 刷新数据", use_container_width=True):
        st.rerun()

    # ---- 路由到对应页面 ----
    page = st.session_state.current_page

    if page == "overview":
        from pages.overview import render as render_overview
        render_overview()
    elif page == "member":
        from pages.member_analysis import render as render_member
        render_member()
    elif page == "activity":
        from pages.activity_analysis import render as render_activity
        render_activity()
    elif page == "insights":
        from pages.insights import render as render_insights
        render_insights()
    elif page == "import":
        render_import_page()


# ================================================================
# 数据导入页面
# ================================================================

def render_import_page():
    st.title("📥 数据导入")
    st.markdown("---")

    # ---- 顶部步骤指引 ----
    st.markdown("""
    <style>
    .step-card {
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        margin-bottom: 1.2rem;
        background: #fafafa;
    }
    .step-card h3 { margin-top: 0; }
    .step-badge {
        display: inline-block;
        background: #e74c3c;
        color: white;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        text-align: center;
        line-height: 28px;
        font-weight: bold;
        margin-right: 8px;
    }
    </style>

    <div style="display:flex; gap:1rem; margin-bottom:1.5rem;">
        <div style="flex:1; text-align:center; padding:0.8rem; background:#fff3f3; border-radius:10px; border:2px solid #e74c3c;">
            <strong style="color:#e74c3c; font-size:1.1rem;">① 下载模板</strong><br>
            <span style="color:#666;">选择类型 → 下载 Excel 模板</span>
        </div>
        <div style="flex:1; text-align:center; padding:0.8rem; background:#f5f5f5; border-radius:10px; border:2px dashed #ccc;">
            <strong style="color:#999; font-size:1.1rem;">② 填写数据</strong><br>
            <span style="color:#999;">按模板格式填写学员/活动数据</span>
        </div>
        <div style="flex:1; text-align:center; padding:0.8rem; background:#f5f5f5; border-radius:10px; border:2px dashed #ccc;">
            <strong style="color:#999; font-size:1.1rem;">③ 上传导入</strong><br>
            <span style="color:#999;">上传文件 → 预览确认 → 导入</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📤 上传数据", "📖 导入指南"])

    with tab1:
        # ================================================================
        # 第一步：选择数据类型 + 下载模板
        # ================================================================
        with st.container():
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("### <span class='step-badge'>1</span> 选择数据类型并下载模板", unsafe_allow_html=True)

            template_options = list(IMPORT_TEMPLATES.keys())
            selected_template = st.selectbox(
                "请选择要导入的数据类型",
                options=template_options,
                format_func=lambda x: f"{x} - {IMPORT_TEMPLATES[x]['description']}",
                key="import_type_select",
            )

            if selected_template:
                template = IMPORT_TEMPLATES[selected_template]

                # 英文字段 → 中文字段 反向映射
                en_to_cn = {}
                for cn, en in COLUMN_ALIASES.items():
                    if en not in en_to_cn:
                        en_to_cn[en] = cn

                def fmt_fields(fields):
                    return ', '.join(
                        f"{en_to_cn.get(f, f)} ({f})" for f in fields
                    )

                col_info, col_dl = st.columns([2, 1])

                with col_info:
                    st.markdown(f"**📋 必填字段**: {fmt_fields(template['required'])}")
                    st.markdown(f"**📝 可选字段**: {fmt_fields(template['optional'])}")
                    st.caption(f"💡 示例列: {template['sample_columns']}")

                with col_dl:
                    import pandas as pd
                    from io import BytesIO
                    import openpyxl

                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # 每种类型加一行示例数据
                        if selected_template == "学员基本信息":
                            sample_data = {
                                "status": ["active"], "name": ["张三"], "gender": ["男"],
                                "class_name": ["盛和塾一班"], "group_name": ["北京一组"],
                                "center": ["北京分中心"], "company_name": ["某某科技"],
                                "position": ["总经理"], "phone": ["13800138000"],
                                "company_address": ["北京市朝阳区建国路88号"],
                                "birthday": ["1985-06-15"],
                                "join_date": ["2024-01-01"],
                                "industry_category": ["制造业"],
                                "industry": ["智能制造"],
                                "company_products": ["工业机器人"],
                                "company_size": ["200-500人"],
                                "referrer": ["李四"],
                            }
                            pd.DataFrame(sample_data, index=[0]).to_excel(writer, index=False, sheet_name='学员信息')
                        elif selected_template == "小组学习会记录":
                            sample_data = {
                                "name": ["张三"], "session_date": ["2024-01-15"],
                                "theme": ["《活法》学习"], "attendance": ["present"],
                                "group_name": ["北京一组"], "reflection": ["收获很大，对经营有帮助"],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='小组学习会')
                        elif selected_template == "班级学习会记录":
                            sample_data = {
                                "name": ["张三"], "session_date": ["2024-01-20"],
                                "theme": ["经营为什么需要哲学"], "attendance": ["present"],
                                "role": ["participant"],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='班级学习会')
                        elif selected_template == "课程参与记录":
                            sample_data = {
                                "name": ["张三"], "course_name": ["经营十二条"],
                                "course_date": ["2024-01-10"], "attendance": ["present"],
                                "score": [88],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='课程记录')
                        elif selected_template == "报告会参与记录":
                            sample_data = {
                                "name": ["张三"], "meeting_name": ["月度经营报告会"],
                                "meeting_date": ["2024-01-25"], "attendance": ["present"],
                                "has_speech": [1], "speech_topic": ["我的经营心得"],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='报告会记录')
                        elif selected_template == "游学参与记录":
                            sample_data = {
                                "name": ["张三"], "destination": ["日本京瓷"],
                                "tour_date": ["2024-03-01"], "duration_days": [5],
                                "harvest_score": [4.5], "reflection": ["深受震撼"],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='游学记录')
                        elif selected_template == "读书打卡记录":
                            sample_data = {
                                "name": ["张三"], "checkin_date": ["2024-01-15"],
                                "book_name": ["活法"], "pages_read": [30],
                                "duration_minutes": [45], "content_summary": ["今天读到利他之心..."],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='读书打卡')
                        elif selected_template == "读书分享记录":
                            sample_data = {
                                "name": ["张三"], "share_date": ["2024-01-20"],
                                "book_name": ["干法"], "share_type": ["读后感"],
                                "content": ["读了这本书让我重新思考工作的意义..."],
                                "quality_score": [4],
                            }
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='读书分享')
                    excel_data = output.getvalue()

                    st.download_button(
                        label=f"📥 下载「{selected_template}」模板",
                        data=excel_data,
                        file_name=f"{selected_template}_模板.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary",
                    )

                st.info("💡 **提示**：下载模板后，按照示例行的格式填写数据，列名支持中英文自动映射（如 `姓名` = `name`）")

            st.markdown('</div>', unsafe_allow_html=True)

        # ================================================================
        # 第二步：上传文件
        # ================================================================
        with st.container():
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("### <span class='step-badge'>2</span> 上传填写好的文件", unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "选择已按模板填写的 Excel (.xlsx) 或 CSV (.csv) 文件",
                type=['xlsx', 'xls', 'csv'],
                help="请先在上方下载模板，按格式填写后再上传",
            )

            if uploaded_file is not None:
                # 保存上传文件
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # 显示预览
                try:
                    import pandas as pd
                    ext = Path(uploaded_file.name).suffix.lower()
                    if ext == '.csv':
                        preview_df = pd.read_csv(tmp_path, encoding='utf-8-sig', nrows=5)
                    else:
                        preview_df = pd.read_excel(tmp_path, nrows=5)

                    st.markdown("##### 👀 数据预览（前5行）")
                    st.dataframe(preview_df, use_container_width=True)

                    # 数据校验摘要
                    total_rows = pd.read_excel(tmp_path).shape[0] if ext != '.csv' else pd.read_csv(tmp_path, encoding='utf-8-sig').shape[0]
                    col_count = preview_df.shape[1]
                    st.caption(f"📊 共检测到 **{total_rows} 行** 数据，**{col_count} 列** 字段")

                    # 导入按钮
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("🚀 开始导入", type="primary", use_container_width=True):
                            with st.spinner("正在导入数据..."):
                                result = import_excel(tmp_path, selected_template)

                            if result['success']:
                                st.success(result['message'])
                                if result['imported'] > 0:
                                    st.balloons()
                            else:
                                st.error(result['message'])

                            if result['errors']:
                                with st.expander("📋 查看详细错误信息"):
                                    for err in result['errors'][:20]:
                                        st.warning(err)
                                    if len(result['errors']) > 20:
                                        st.caption(f"...还有 {len(result['errors'])-20} 条错误")

                    with col2:
                        reimport_key = f"reimport_{datetime.now().timestamp()}"
                        if st.button("↩️ 重新选择", use_container_width=True):
                            st.rerun()

                except Exception as e:
                    st.error(f"文件读取失败: {str(e)}")

                finally:
                    # 清理临时文件
                    import os
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
            else:
                # 未上传文件时，显示友好提示
                st.info("📂 请先在 **第1步** 下载模板，填写完成后返回此处上传")

            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown(get_import_guide())

        # 导入历史
        st.markdown("---")
        st.markdown("### 📋 最近导入记录")
        from database import get_connection
        conn = get_connection()
        import pandas as pd
        logs = pd.read_sql_query(
            """SELECT id, import_date, file_name, table_name, record_count, status
               FROM import_log ORDER BY id DESC LIMIT 20""",
            conn
        )
        conn.close()
        if not logs.empty:
            st.dataframe(logs, use_container_width=True, hide_index=True)
        else:
            st.info("暂无导入记录")


if __name__ == "__main__":
    main()
