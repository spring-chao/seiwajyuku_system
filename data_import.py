"""
盛和塾运营管理系统 - 数据导入模块
支持从 Excel/CSV 导入各业务表数据
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import traceback

from database import get_connection, execute_insert, execute_query, init_database


# ---- 导入模板定义 ----

IMPORT_TEMPLATES = {
    "学员基本信息": {
        "table": "members",
        "required": ["name"],
        "optional": ["status", "gender", "class_name", "group_name", "center",
                     "company_name", "position", "phone", "company_address",
                     "birthday", "join_date", "industry_category", "industry",
                     "company_products", "company_size", "referrer",
                     "email", "wechat", "notes"],
        "description": "导入学员基本档案信息",
        "sample_columns": "是否在册(status), 姓名(name), 性别(gender), 所属班级(class_name), 组名(group_name), 所在分中心(center), 公司名称(company_name), 职务(position), 手机号码(phone), 公司地址(company_address), 生日时间(birthday), 入塾日期(join_date), 行业分类(industry_category), 所属行业(industry), 公司产品(company_products), 规模(company_size), 推荐人(referrer)",
        "unique_keys": ["name", "phone"],  # 用于去重/更新判断
    },
    "小组学习会记录": {
        "table": "group_sessions",
        "required": ["name", "session_date"],
        "optional": ["theme", "attendance", "reflection", "group_name", "facilitator", "duration_minutes"],
        "description": "导入各小组学习会的参与记录",
        "sample_columns": "姓名(name), 日期(session_date), 主题(theme), 出勤(attendance), 小组(group_name)",
        "member_key": "name",
        "unique_keys": ["member_id", "session_date"],
    },
    "班级学习会记录": {
        "table": "class_sessions",
        "required": ["name", "session_date"],
        "optional": ["theme", "attendance", "role", "notes"],
        "description": "导入班级学习会的参与记录",
        "sample_columns": "姓名(name), 日期(session_date), 主题(theme), 出勤(attendance), 角色(role)",
        "member_key": "name",
        "unique_keys": ["member_id", "session_date"],
    },
    "课程参与记录": {
        "table": "courses",
        "required": ["name", "course_name", "course_date"],
        "optional": ["attendance", "score", "evaluation", "certificate"],
        "description": "导入课程参与情况",
        "sample_columns": "姓名(name), 课程名(course_name), 日期(course_date), 出勤(attendance), 成绩(score)",
        "member_key": "name",
        "unique_keys": ["member_id", "course_name", "course_date"],
    },
    "报告会参与记录": {
        "table": "report_meetings",
        "required": ["name", "meeting_name", "meeting_date"],
        "optional": ["attendance", "has_speech", "speech_topic", "feedback"],
        "description": "导入报告会参与记录",
        "sample_columns": "姓名(name), 报告会(meeting_name), 日期(meeting_date), 出勤(attendance), 是否发言(has_speech)",
        "member_key": "name",
        "unique_keys": ["member_id", "meeting_name", "meeting_date"],
    },
    "游学参与记录": {
        "table": "study_tours",
        "required": ["name", "destination", "tour_date"],
        "optional": ["duration_days", "harvest_score", "reflection"],
        "description": "导入游学参与记录",
        "sample_columns": "姓名(name), 游学地(destination), 日期(tour_date), 天数(duration_days), 收获评分(harvest_score)",
        "member_key": "name",
        "unique_keys": ["member_id", "destination", "tour_date"],
    },
    "读书打卡记录": {
        "table": "reading_checkins",
        "required": ["name", "checkin_date"],
        "optional": ["book_name", "pages_read", "duration_minutes", "content_summary"],
        "description": "导入读书打卡数据",
        "sample_columns": "姓名(name), 日期(checkin_date), 书名(book_name), 页数(pages_read), 时长(分钟/duration_minutes)",
        "member_key": "name",
        "unique_keys": ["member_id", "checkin_date"],
    },
    "读书分享记录": {
        "table": "reading_shares",
        "required": ["name", "share_date", "book_name"],
        "optional": ["share_type", "content", "quality_score", "duration_minutes"],
        "description": "导入读书分享记录",
        "sample_columns": "姓名(name), 日期(share_date), 书名(book_name), 分享类型(share_type), 质量评分(quality_score)",
        "member_key": "name",
        "unique_keys": ["member_id", "share_date", "book_name"],
    },
}

# 中英文列名映射
COLUMN_ALIASES = {
    '姓名': 'name', '名字': 'name', '学员': 'name', '学员姓名': 'name',
    '手机': 'phone', '手机号': 'phone', '电话': 'phone',
    '性别': 'gender',
    '班级': 'class_name', '所属班级': 'class_name',
    '分中心': 'center', '中心': 'center', '所属中心': 'center',
    '入塾日期': 'join_date', '入塾时间': 'join_date', '加入日期': 'join_date',
    '公司': 'company_name', '公司名': 'company_name', '企业': 'company_name', '单位': 'company_name',
    '职位': 'position', '职务': 'position', '岗位': 'position',
    '推荐人': 'referrer', '介绍人': 'referrer',
    '邮箱': 'email', 'Email': 'email',
    '微信': 'wechat', '微信号': 'wechat',
    '是否在册': 'status', '在册': 'status', '状态': 'status',
    '组名': 'group_name', '所属组': 'group_name', '小组': 'group_name',
    '公司地址': 'company_address', '地址': 'company_address',
    '生日': 'birthday', '生日时间': 'birthday', '出生日期': 'birthday', '生日日期': 'birthday',
    '行业分类': 'industry_category',
    '所属行业': 'industry', '行业': 'industry',
    '公司产品': 'company_products', '产品': 'company_products',
    '规模': 'company_size', '公司规模': 'company_size', '企业规模': 'company_size',
    '日期': 'session_date', '学习日期': 'session_date', '活动日期': 'session_date',
    '主题': 'theme', '学习主题': 'theme', '内容': 'theme',
    '出勤': 'attendance', '是否出席': 'attendance', '参与情况': 'attendance', '状态': 'attendance',
    '心得': 'reflection', '感想': 'reflection', '收获': 'reflection',
    '小组': 'group_name', '小组名': 'group_name', '所属小组': 'group_name',
    '主持人': 'facilitator', '组长': 'facilitator',
    '时长': 'duration_minutes', '时长(分钟)': 'duration_minutes', '分钟': 'duration_minutes',
    '课程名': 'course_name', '课程名称': 'course_name', '课程': 'course_name',
    '课程日期': 'course_date', '上课日期': 'course_date',
    '成绩': 'score', '评分': 'score', '分数': 'score',
    '评价': 'evaluation', '自我评价': 'evaluation',
    '证书': 'certificate', '是否获证': 'certificate',
    '报告会': 'meeting_name', '报告会名': 'meeting_name', '会议名称': 'meeting_name',
    '报告会日期': 'meeting_date', '会议日期': 'meeting_date',
    '是否发言': 'has_speech', '发言': 'has_speech',
    '发言主题': 'speech_topic',
    '反馈': 'feedback', '意见': 'feedback',
    '游学地': 'destination', '目的': 'destination', '地点': 'destination', '游学地点': 'destination',
    '游学日期': 'tour_date', '出行日期': 'tour_date',
    '天数': 'duration_days', '游学天数': 'duration_days', '持续天数': 'duration_days',
    '收获评分': 'harvest_score', '游学评分': 'harvest_score', '评分(1-5)': 'harvest_score',
    '游学心得': 'reflection',
    '打卡日期': 'checkin_date', '签到日期': 'checkin_date',
    '书名': 'book_name', '书籍': 'book_name', '书名/文章': 'book_name',
    '阅读页数': 'pages_read', '页数': 'pages_read',
    '阅读时长(分钟)': 'duration_minutes',
    '阅读摘要': 'content_summary', '今日摘要': 'content_summary', '内容摘要': 'content_summary',
    '分享日期': 'share_date',
    '分享类型': 'share_type', '方式': 'share_type',
    '分享内容': 'content', '分享摘要': 'content',
    '质量评分': 'quality_score', '分享评分': 'quality_score',
    '分享时长(分钟)': 'duration_minutes',
    '备注': 'notes', '备注说明': 'notes',
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """自动将中文列名映射为英文字段名"""
    renamed = {}
    for col in df.columns:
        col_clean = col.strip()
        if col_clean in COLUMN_ALIASES:
            renamed[col] = COLUMN_ALIASES[col_clean]
        else:
            # 原样保留（可能是英文字段名）
            renamed[col] = col_clean
    return df.rename(columns=renamed)


def resolve_member_id(name: str, conn) -> Optional[int]:
    """根据学员姓名查找成员ID（支持模糊匹配）"""
    import sqlite3
    cur = conn.cursor()
    # 精确匹配
    cur.execute("SELECT id FROM members WHERE name=?", (name.strip(),))
    row = cur.fetchone()
    if row:
        return row[0]
    # 模糊匹配
    cur.execute("SELECT id, name FROM members WHERE name LIKE ?", (f"%{name.strip()}%",))
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    elif len(rows) > 1:
        return None  # 多匹配，需要用户确认
    return None


def import_excel(file_path: str, template_key: str) -> Dict:
    """
    导入Excel/CSV文件到指定表
    
    返回: {
        'success': bool,
        'imported': int,
        'skipped': int,
        'errors': List[str],
        'message': str
    }
    """
    template = IMPORT_TEMPLATES.get(template_key)
    if not template:
        return {'success': False, 'imported': 0, 'skipped': 0,
                'errors': [f'未知模板: {template_key}'], 'message': '导入失败'}

    result = {'success': True, 'imported': 0, 'updated': 0, 'duplicate': 0, 'skipped': 0, 'errors': [], 'message': ''}

    try:
        # 读取文件
        ext = Path(file_path).suffix.lower()
        if ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            return {'success': False, 'imported': 0, 'skipped': 0,
                    'errors': [f'不支持的文件格式: {ext}'], 'message': '导入失败'}

        # 标准化列名
        df = normalize_columns(df)

        # 检查必填字段
        missing = [c for c in template['required'] if c not in df.columns]
        if missing:
            return {'success': False, 'imported': 0, 'skipped': 0,
                    'errors': [f'缺少必填列: {", ".join(missing)}'],
                    'message': '导入失败，请检查表头'}

        # 标准化学员状态值（中文 → 英文）
        STATUS_VALUE_MAP = {
            '在册': 'active', '活跃': 'active', '正常': 'active',
            '流失': 'churned', '退塾': 'churned', '退出': 'churned',
            '暂停': 'paused', '停课': 'paused', '休学': 'paused',
        }
        if 'status' in df.columns:
            df['status'] = df['status'].map(lambda v: STATUS_VALUE_MAP.get(str(v).strip(), v) if v else v)

        # 清理数据
        df = df.replace({pd.NA: None, pd.NaT: None, '': None, float('nan'): None})

        conn = get_connection()
        cur = conn.cursor()

        table = template['table']
        has_member_key = 'member_key' in template

        for idx, row in df.iterrows():
            try:
                record = {}
                member_id = None

                # 如果有会员映射，先解析member_id
                if has_member_key and template['member_key'] == 'name':
                    name = str(row.get('name', '')).strip()
                    if not name:
                        result['skipped'] += 1
                        result['errors'].append(f"第{idx+2}行: 姓名为空")
                        continue
                    member_id = resolve_member_id(name, conn)
                    if member_id is None:
                        # 尝试查找相似姓名
                        cur.execute(
                            "SELECT id, name FROM members WHERE name LIKE ?",
                            (f"%{name.replace('%', '')}%",)
                        )
                        candidates = cur.fetchall()
                        if len(candidates) == 1:
                            member_id = candidates[0][0]
                        elif len(candidates) > 1:
                            result['skipped'] += 1
                            result['errors'].append(f"第{idx+2}行: 姓名'{name}'匹配到多个学员，跳过")
                            continue
                        else:
                            result['skipped'] += 1
                            result['errors'].append(f"第{idx+2}行: 未找到学员'{name}'，请先导入学员信息")
                            continue

                # 构建记录字段
                all_fields = template['required'] + template['optional']
                for field in all_fields:
                    if field in row and row[field] is not None:
                        val = row[field]
                        # 处理布尔值
                        if field == 'has_speech':
                            if isinstance(val, str):
                                val = 1 if val.strip() in ['是', '有', '1', 'yes', 'Yes', 'Y'] else 0
                            else:
                                val = int(bool(val))
                        # 处理数字
                        elif field in ['score', 'pages_read', 'duration_minutes',
                                       'duration_days', 'harvest_score', 'quality_score']:
                            try:
                                val = float(val) if val is not None else None
                            except (ValueError, TypeError):
                                val = None

                        if val is not None:
                            record[field] = val

                # 添加member_id
                if member_id is not None:
                    record['member_id'] = member_id

                # 转换日期/时间戳类型为字符串（SQLite 不支持 Timestamp）
                from datetime import datetime
                for k, v in list(record.items()):
                    if hasattr(v, 'isoformat'):
                        if pd.isna(v):
                            del record[k]
                        else:
                            # 日期只保留 YYYY-MM-DD，不显示 T00:00:00
                            if isinstance(v, (datetime, pd.Timestamp)):
                                record[k] = v.strftime('%Y-%m-%d')
                            else:
                                record[k] = str(v)
                    elif isinstance(v, (float, int)) and pd.isna(v):
                        pass  # 保持原样，SQLite 可接受 None

                # 插入/更新
                if record:
                    # 学员信息表：按姓名(+手机号)去重，已存在则更新，不存在则插入
                    if table == 'members' and 'name' in record:
                        name = record['name']
                        phone = record.get('phone', '')
                        matched_id = None

                        # 策略1：有手机号 → 按姓名+手机号精确匹配
                        if phone:
                            cur.execute(
                                "SELECT id FROM members WHERE name=? AND phone=?",
                                (name, phone)
                            )
                            row = cur.fetchone()
                            if row:
                                matched_id = row[0]

                        # 策略2：无手机号或姓名+手机号没匹配到 → 按姓名精确匹配（仅当唯一）
                        if matched_id is None:
                            cur.execute("SELECT id FROM members WHERE name=?", (name,))
                            rows = cur.fetchall()
                            if len(rows) == 1:
                                matched_id = rows[0][0]
                            elif len(rows) > 1:
                                # 同名多人且无手机号（或手机号不同）→ 跳过，让用户补充
                                if phone:
                                    result['skipped'] += 1
                                    result['errors'].append(
                                        f"第{idx+2}行: 姓名'{name}'匹配到多条记录，指定手机号'{phone}'未匹配到任何记录，跳过"
                                    )
                                else:
                                    result['skipped'] += 1
                                    result['errors'].append(
                                        f"第{idx+2}行: 姓名'{name}'匹配到多条记录，请在Excel中添加手机号列以区分，跳过"
                                    )
                                continue

                        if matched_id is not None:
                            set_clause = ', '.join(f"{k}=?" for k in record.keys())
                            cur.execute(
                                f"UPDATE {table} SET {set_clause} WHERE id=?",
                                tuple(record.values()) + (matched_id,)
                            )
                            result['updated'] += 1
                            continue

                    # 对于非 members 表，检查 unique_keys 去重
                    if table != 'members' and 'unique_keys' in template:
                        uk_fields = template['unique_keys']
                        # 确保所有唯一键字段都在 record 中
                        if all(k in record for k in uk_fields):
                            conditions = ' AND '.join(f"{k}=?" for k in uk_fields)
                            cur.execute(f"SELECT id FROM {table} WHERE {conditions}",
                                        tuple(record[k] for k in uk_fields))
                            if cur.fetchone():
                                result['duplicate'] += 1
                                continue

                    columns = ', '.join(record.keys())
                    placeholders = ', '.join(['?'] * len(record))
                    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    cur.execute(sql, tuple(record.values()))
                    result['imported'] += 1

            except Exception as e:
                result['skipped'] += 1
                result['errors'].append(f"第{idx+2}行: {str(e)}")

        conn.commit()
        conn.close()

        # 记录导入日志
        log_data = {
            'file_name': Path(file_path).name,
            'table_name': table,
            'record_count': result['imported'],
            'status': 'success' if not result['errors'] else 'partial',
            'error_message': '; '.join(result['errors'][:5]) if result['errors'] else ''
        }
        execute_insert('import_log', log_data)

        parts = []
        if result['imported'] > 0:
            parts.append(f"✅ 成功导入 {result['imported']} 条新记录")
        if result['updated'] > 0:
            parts.append(f"🔄 更新 {result['updated']} 条已有记录")
        if result['duplicate'] > 0:
            parts.append(f"⏭️ 跳过 {result['duplicate']} 条重复记录")
        if result['skipped'] > 0:
            parts.append(f"⚠️ 跳过 {result['skipped']} 条错误记录")
        if result['errors']:
            parts.append(f"（{len(result['errors'])} 个警告）")
        msg = '，'.join(parts) if parts else "没有导入任何记录"
        result['message'] = msg

    except Exception as e:
        result['success'] = False
        result['message'] = f'导入失败: {str(e)}'
        result['errors'].append(traceback.format_exc())

    return result


def get_data_overview() -> Dict:
    """获取所有表的数据概览"""
    conn = get_connection()
    cur = conn.cursor()

    tables = {
        'members': '学员信息',
        'companies': '公司情况',
        'group_sessions': '小组学习会',
        'class_sessions': '班级学习会',
        'courses': '课程记录',
        'report_meetings': '报告会记录',
        'study_tours': '游学记录',
        'reading_checkins': '读书打卡',
        'reading_shares': '读书分享',
    }

    overview = {}
    for table, label in tables.items():
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        if table != 'members':
            cur.execute(f"SELECT COUNT(DISTINCT member_id) FROM {table}")
            member_count = cur.fetchone()[0]
        else:
            cur.execute("SELECT COUNT(DISTINCT center) FROM members")
            center_count = cur.fetchone()[0]
            member_count = count
            overview['center_count'] = center_count

        overview[table] = {'label': label, 'count': count, 'member_count': member_count}

    conn.close()
    return overview


# ---- Streamlit 导出模板下载 ----

def get_sample_dataframe(template_key: str) -> pd.DataFrame:
    """生成示例数据模板 DataFrame"""
    template = IMPORT_TEMPLATES.get(template_key)
    if not template:
        return pd.DataFrame()

    all_cols = template['required'] + template['optional']
    return pd.DataFrame(columns=all_cols)


def get_import_guide() -> str:
    """生成导入指南 Markdown"""
    guide = """
## 📖 数据导入指南

### 支持的数据类型（共8类）

| 数据类型 | 必填字段 | 说明 |
|----------|----------|------|
| 学员基本信息 | 姓名(name) | 先导入学员信息，再导入其他数据。支持 是否在册/所属班级/组名/公司地址/生日/行业分类/所属行业/公司产品/规模 等字段 |
| 小组学习会记录 | 姓名,日期 | 需学员信息已存在 |
| 班级学习会记录 | 姓名,日期 | 需学员信息已存在 |
| 课程参与记录 | 姓名,课程名,课程日期 | 需学员信息已存在 |
| 报告会参与记录 | 姓名,报告会名,日期 | 需学员信息已存在 |
| 游学参与记录 | 姓名,游学地,日期 | 需学员信息已存在 |
| 读书打卡记录 | 姓名,日期 | 需学员信息已存在 |
| 读书分享记录 | 姓名,日期,书名 | 需学员信息已存在 |

### ⚠️ 注意事项
1. **先导入学员信息**，再导入其他活动数据（系统通过"姓名"自动匹配学员）
2. 支持 Excel (.xlsx) 和 CSV (.csv) 格式
3. 列名支持中英文自动映射，如"姓名"→"name"，"日期"→"session_date"
4. 日期格式建议：YYYY-MM-DD
5. 每次导入会记录到导入日志，可追溯
    """
    return guide
