-- 数据库结构导出 (自动生成)
-- SQLite 格式

-- Table: class_sessions
CREATE TABLE class_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            theme TEXT,
            attendance TEXT DEFAULT 'present',
            role TEXT,                     -- 角色: participant / speaker / organizer
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

-- Table: companies
CREATE TABLE companies (
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
        );

-- Table: courses
CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            course_date TEXT NOT NULL,
            attendance TEXT DEFAULT 'present',
            score REAL,                    -- 成绩/评分
            evaluation TEXT,               -- 自我评价
            certificate TEXT,              -- 是否获得证书
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

-- Table: group_sessions
CREATE TABLE group_sessions (
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
        );

-- Table: import_log
CREATE TABLE import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_date TEXT DEFAULT (datetime('now','localtime')),
            file_name TEXT,
            table_name TEXT,
            record_count INTEGER,
            status TEXT DEFAULT 'success',
            error_message TEXT
        );

-- Table: members
CREATE TABLE members (
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
        , group_name TEXT, company_address TEXT, birthday TEXT, industry_category TEXT, industry TEXT, company_products TEXT, company_size TEXT);

-- Table: reading_checkins
CREATE TABLE reading_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            book_name TEXT,
            pages_read INTEGER,
            duration_minutes INTEGER,
            content_summary TEXT,          -- 今日阅读摘要
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

-- Table: reading_shares
CREATE TABLE reading_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            share_date TEXT NOT NULL,
            book_name TEXT NOT NULL,
            share_type TEXT,               -- 口头分享 / 书面分享 / 小组分享
            content TEXT,                  -- 分享内容
            quality_score INTEGER,         -- 质量评分 1-5
            duration_minutes INTEGER,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

-- Table: report_meetings
CREATE TABLE report_meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            meeting_name TEXT NOT NULL,
            meeting_date TEXT NOT NULL,
            attendance TEXT DEFAULT 'present',
            has_speech INTEGER DEFAULT 0,  -- 是否发言 0/1
            speech_topic TEXT,             -- 发言主题
            feedback TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

-- Table: sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- Table: study_tours
CREATE TABLE study_tours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            destination TEXT NOT NULL,      -- 游学地
            tour_date TEXT NOT NULL,
            duration_days INTEGER,
            harvest_score INTEGER,         -- 收获评分 1-5
            reflection TEXT,               -- 游学心得
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

-- Table: suggestions_log
CREATE TABLE suggestions_log (
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
        );

-- Table: system_config
CREATE TABLE system_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );
