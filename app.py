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
from data_import import get_import_guide, IMPORT_TEMPLATES, import_excel, get_sample_dataframe
from suggestions import generate_suggestions

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

    tab1, tab2 = st.tabs(["📤 上传数据", "📖 导入指南"])

    with tab1:
        st.markdown("### 第一步：选择数据类型")

        template_options = list(IMPORT_TEMPLATES.keys())
        selected_template = st.selectbox(
            "请选择要导入的数据类型",
            options=template_options,
            format_func=lambda x: f"{x} - {IMPORT_TEMPLATES[x]['description']}",
        )

        if selected_template:
            template = IMPORT_TEMPLATES[selected_template]
            st.markdown(f"**必填字段**: {', '.join(template['required'])}")
            st.markdown(f"**可选字段**: {', '.join(template['optional'])}")
            st.caption(f"示例列: {template['sample_columns']}")

            # 示例模板下载
            st.markdown("---")
            col1, col2 = st.columns([2, 2])
            with col1:
                sample_df = get_sample_dataframe(selected_template)
                if not sample_df.empty:
                    import pandas as pd
                    from io import BytesIO
                    import openpyxl

                    # 生成示例Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # 加一行示例数据
                        if selected_template == "学员基本信息":
                            sample_data = {"name": ["张三"], "phone": ["13800138000"],
                                           "class_name": ["盛和塾一班"], "center": ["北京分中心"],
                                           "join_date": ["2024-01-01"]}
                            pd.DataFrame(sample_data).to_excel(writer, index=False, sheet_name='学员信息')
                        else:
                            sample_df.to_excel(writer, index=False, sheet_name='数据')
                    excel_data = output.getvalue()

                    st.download_button(
                        label=f"📥 下载 {selected_template} 模板",
                        data=excel_data,
                        file_name=f"{selected_template}_模板.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

            with col2:
                st.markdown("")
                st.markdown("💡 **提示**: 列名支持中英文自动映射")
                st.markdown("如: `姓名` → `name`, `日期` → `session_date`")

            # 文件上传
            st.markdown("---")
            st.markdown("### 第二步：上传文件")

            uploaded_file = st.file_uploader(
                "选择 Excel (.xlsx) 或 CSV (.csv) 文件",
                type=['xlsx', 'xls', 'csv'],
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

                    st.markdown("#### 数据预览（前5行）")
                    st.dataframe(preview_df, use_container_width=True)

                    # 导入按钮
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


from datetime import datetime

if __name__ == "__main__":
    main()
