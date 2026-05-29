"""
盛和塾运营管理系统 - 数据库模块
SQLite 数据库，10张表覆盖全部业务数据
"""

import sqlite3
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

DB_PATH = Path(__file__).parent / "seiwajyuku.db"


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """初始化数据库，创建所有表"""
    conn = get_connection()
    cur = conn.cursor()

    # 1. 学员基本信息
    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            gender TEXT,
            class_name TEXT,              -- 班级
            center TEXT,                  -- 分中心
            join_date TEXT,               -- 入塾日期 YYYY-MM-DD
            company_name TEXT,            -- 公司名
            position TEXT,                -- 职位
            referrer TEXT,                -- 推荐人
            email TEXT,
            wechat TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active', -- active / paused / churned
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 2. 公司情况
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            industry TEXT,                -- 行业
            scale TEXT,                   -- 规模（人数）
            annual_revenue TEXT,          -- 年营收
            founded_year TEXT,            -- 成立年份
            city TEXT,
            website TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 3. 小组学习会记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS group_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,     -- YYYY-MM-DD
            theme TEXT,                    -- 主题
            attendance TEXT DEFAULT 'present', -- present / absent / leave
            reflection TEXT,               -- 心得/感想
            group_name TEXT,               -- 小组名
            facilitator TEXT,              -- 主持人
            duration_minutes INTEGER,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 4. 班级学习会记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS class_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            theme TEXT,
            attendance TEXT DEFAULT 'present',
            role TEXT,                     -- 角色: participant / speaker / organizer
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 5. 课程参与记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            course_date TEXT NOT NULL,
            attendance TEXT DEFAULT 'present',
            score REAL,                    -- 成绩/评分
            evaluation TEXT,               -- 自我评价
            certificate TEXT,              -- 是否获得证书
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 6. 报告会参与记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS report_meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            meeting_name TEXT NOT NULL,
            meeting_date TEXT NOT NULL,
            attendance TEXT DEFAULT 'present',
            has_speech INTEGER DEFAULT 0,  -- 是否发言 0/1
            speech_topic TEXT,             -- 发言主题
            feedback TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 7. 游学参与记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS study_tours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            destination TEXT NOT NULL,      -- 游学地
            tour_date TEXT NOT NULL,
            duration_days INTEGER,
            harvest_score INTEGER,         -- 收获评分 1-5
            reflection TEXT,               -- 游学心得
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 8. 读书打卡记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reading_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            book_name TEXT,
            pages_read INTEGER,
            duration_minutes INTEGER,
            content_summary TEXT,          -- 今日阅读摘要
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 9. 读书分享记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reading_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            share_date TEXT NOT NULL,
            book_name TEXT NOT NULL,
            share_type TEXT,               -- 口头分享 / 书面分享 / 小组分享
            content TEXT,                  -- 分享内容
            quality_score INTEGER,         -- 质量评分 1-5
            duration_minutes INTEGER,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 10. 运营建议日志
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suggestions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_date TEXT NOT NULL,
            analysis_dimension TEXT,        -- 分析维度
            member_id INTEGER,
            suggestion_type TEXT,           -- individual / group / system
            title TEXT,
            content TEXT,
            priority TEXT DEFAULT 'medium', -- high / medium / low
            is_adopted INTEGER DEFAULT 0,
            adopted_date TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    # 11. 系统配置
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 12. 数据导入日志
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_date TEXT DEFAULT (datetime('now','localtime')),
            file_name TEXT,
            table_name TEXT,
            record_count INTEGER,
            status TEXT DEFAULT 'success',
            error_message TEXT
        )
    """)

    # 创建索引
    cur.execute("CREATE INDEX IF NOT EXISTS idx_member_name ON members(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_member_center ON members(center)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_member_class ON members(class_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_group_member ON group_sessions(member_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_group_date ON group_sessions(session_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_class_member ON class_sessions(member_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_course_member ON courses(member_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_report_member ON report_meetings(member_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tour_member ON study_tours(member_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_checkin_member ON reading_checkins(member_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_checkin_date ON reading_checkins(checkin_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_share_member ON reading_shares(member_id)")

    # 插入默认配置
    default_configs = [
        ('stratification_weights',
         '{"participation":30,"reading":20,"trend":25,"diversity":25}'),
        ('threshold_core', '85'),
        ('threshold_stable', '70'),
        ('threshold_potential', '50'),
        ('threshold_at_risk', '30'),
        ('system_version', '1.0.0'),
        ('last_analysis_date', ''),
    ]
    for key, value in default_configs:
        cur.execute("""
            INSERT OR IGNORE INTO system_config (key, value)
            VALUES (?, ?)
        """, (key, value))

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


# ---- 通用 CRUD 操作 ----

def execute_query(sql: str, params: tuple = ()) -> List[Dict]:
    """执行查询并返回字典列表"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def execute_insert(table: str, data: Dict) -> int:
    """插入一条记录，返回自增ID"""
    conn = get_connection()
    cur = conn.cursor()
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    cur.execute(sql, tuple(data.values()))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def execute_update(table: str, data: Dict, where: str, where_params: tuple = ()):
    """更新记录"""
    conn = get_connection()
    cur = conn.cursor()
    set_clause = ', '.join([f"{k}=?" for k in data.keys()])
    sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
    cur.execute(sql, tuple(data.values()) + where_params)
    conn.commit()
    conn.close()


def execute_delete(table: str, where: str, params: tuple = ()):
    """删除记录"""
    conn = get_connection()
    cur = conn.cursor()
    sql = f"DELETE FROM {table} WHERE {where}"
    cur.execute(sql, params)
    conn.commit()
    conn.close()


def table_to_df(table: str, where: str = "", params: tuple = ()) -> pd.DataFrame:
    """将表查询结果转为 DataFrame"""
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY id"
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def get_statistics(table: str) -> Dict:
    """获取表的基本统计"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) as total FROM {table}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(DISTINCT member_id) as members FROM {table}")
    members = cur.fetchone()[0] if total > 0 else 0
    conn.close()
    return {"total_records": total, "unique_members": members}


# ---- 学员分层相关查询 ----

def get_member_participation_summary(member_id: int) -> Dict:
    """获取单个学员的参与度汇总"""
    conn = get_connection()
    cur = conn.cursor()

    # 小组学习会
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
        FROM group_sessions WHERE member_id=?
    """, (member_id,))
    gs = dict(cur.fetchone())

    # 班级学习会
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
        FROM class_sessions WHERE member_id=?
    """, (member_id,))
    cs = dict(cur.fetchone())

    # 课程
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present
        FROM courses WHERE member_id=?
    """, (member_id,))
    co = dict(cur.fetchone())

    # 报告会
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN attendance='present' THEN 1 ELSE 0 END) as present,
               SUM(has_speech) as speeches
        FROM report_meetings WHERE member_id=?
    """, (member_id,))
    rm = dict(cur.fetchone())

    # 游学
    cur.execute("""
        SELECT COUNT(*) as total,
               AVG(harvest_score) as avg_harvest
        FROM study_tours WHERE member_id=?
    """, (member_id,))
    st = dict(cur.fetchone())

    # 读书打卡
    cur.execute("""
        SELECT COUNT(*) as total_checkins,
               COUNT(DISTINCT book_name) as unique_books
        FROM reading_checkins WHERE member_id=?
    """, (member_id,))
    rc = dict(cur.fetchone())

    # 读书分享
    cur.execute("""
        SELECT COUNT(*) as total_shares,
               AVG(quality_score) as avg_quality
        FROM reading_shares WHERE member_id=?
    """, (member_id,))
    rs = dict(cur.fetchone())

    conn.close()

    def rate(num, den):
        return round(num / den * 100, 1) if den > 0 else 0.0

    return {
        "group_session": {"total": gs["total"], "present": gs["present"],
                          "rate": rate(gs["present"], gs["total"])},
        "class_session": {"total": cs["total"], "present": cs["present"],
                          "rate": rate(cs["present"], cs["total"])},
        "course": {"total": co["total"], "present": co["present"],
                   "rate": rate(co["present"], co["total"])},
        "report_meeting": {"total": rm["total"], "present": rm["present"],
                           "speeches": rm["speeches"] or 0,
                           "rate": rate(rm["present"], rm["total"])},
        "study_tour": {"total": st["total"], "avg_harvest": round(st["avg_harvest"] or 0, 1)},
        "reading_checkin": {"total": rc["total_checkins"],
                            "unique_books": rc["unique_books"] or 0},
        "reading_share": {"total": rs["total_shares"],
                          "avg_quality": round(rs["avg_quality"] or 0, 1)},
    }


if __name__ == "__main__":
    init_database()
