"""
盛和塾运营管理系统 - 测试数据生成器
生成完整的模拟数据用于测试系统功能
"""

import random
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_database, get_connection, execute_insert, execute_query


# ---- 模拟数据 ----

CENTERS = [
    "北京分中心", "上海分中心", "广州分中心", "深圳分中心",
    "杭州分中心", "成都分中心", "南京分中心", "武汉分中心",
]

CLASSES = [
    "盛和塾卓越一班", "盛和塾卓越二班", "盛和塾卓越三班",
    "盛和塾精进一班", "盛和塾精进二班",
]

INDUSTRIES = [
    "制造业", "互联网科技", "教育培训", "医疗健康",
    "金融服务", "餐饮服务", "房地产", "文化传媒",
    "零售贸易", "物流运输",
]

BOOKS = [
    "活法", "干法", "心法", "经营十二条", "六项精进",
    "京瓷哲学", "阿米巴经营", "领导者的资质", "提高心性，拓展经营",
    "论语与算盘", "了凡四训", "道德经", "王阳明心学",
    "高效能人士的七个习惯", "从优秀到卓越",
]

SESSION_THEMES_GROUP = [
    "稻盛哲学学习", "经营体验分享", "读书心得交流",
    "企业参访备战", "年度目标研讨", "团队建设",
    "阿米巴经营实践", "六项精进实践分享",
]

SESSION_THEMES_CLASS = [
    "月度学习总结", "季度经营分析", "年度规划会议",
    "专家专题讲座", "企业互访交流", "毕业典礼暨迎新会",
]

COURSE_NAMES = [
    "盛和塾经营入门课程", "阿米巴经营实战课程",
    "稻盛哲学精读课程", "领导力提升课程",
    "企业文化塑造课程", "年度经营计划课程",
]

MEETING_NAMES = [
    "年度经营报告会", "季度成果报告会", "优秀塾生分享会",
    "专题研究报告会", "新年展望报告会",
]

TOUR_DESTINATIONS = [
    "日本京瓷参访", "日本京都游学", "深圳华为参访",
    "杭州阿里巴巴参访", "苏州优秀塾生企业参访",
    "成都标杆企业考察",
]

NAMES = [
    "张伟", "王芳", "李强", "刘洋", "陈静", "杨磊", "赵敏",
    "黄勇", "周洁", "吴昊", "徐丽", "孙明", "马超", "朱艳",
    "胡波", "郭娟", "林峰", "何婷", "高明", "罗琳", "梁涛",
    "宋倩", "唐杰", "韩晶", "曹鹏", "邓雪", "许峰", "彭慧",
    "苏晨", "潘峰", "田甜", "范志", "汪洋", "石磊", "余丹",
    "赖敏", "蔡伟", "袁媛", "姜帆", "程亮", "魏欣", "吕波",
    "丁莉", "任杰", "沈静", "姚远", "卢芳", "蒋平", "蔡琴",
    "贾明", "江雪", "邹伟", "曾敏", "邱峰", "林琳",
]


def generate_sample_data(member_count: int = 50, months: int = 6):
    """
    生成模拟数据
    
    参数:
        member_count: 学员数量
        months: 数据覆盖月数
    """
    print(f"正在生成模拟数据: {member_count} 学员, {months} 个月...")

    init_database()
    conn = get_connection()
    cur = conn.cursor()

    today = datetime.now()
    member_ids = []

    # ================================================================
    # 1. 学员信息
    # ================================================================
    print("正在生成学员信息...")
    selected_names = random.sample(NAMES, min(member_count, len(NAMES)))

    for i, name in enumerate(selected_names):
        center = random.choice(CENTERS)
        class_name = random.choice(CLASSES)
        join_date = today - timedelta(days=random.randint(30, 730))
        company_name = f"{['北京','上海','广州','深圳','杭州'][i % 5]}{random.choice(['创新','卓越','共赢','远见','博学'])}科技有限公司"
        industry = random.choice(INDUSTRIES)
        referrer = random.choice(selected_names[:10]) if i >= 10 else "盛和塾"

        member_data = {
            'name': name,
            'phone': f"1{random.choice(['38','58','86','35','59'])}{random.randint(10000000, 99999999)}",
            'gender': random.choice(['男', '女']),
            'class_name': class_name,
            'center': center,
            'join_date': join_date.strftime('%Y-%m-%d'),
            'company_name': company_name,
            'position': random.choice(['总经理', 'CEO', '董事长', '部门经理', '创始人', '合伙人']),
            'referrer': referrer,
            'notes': '',

        }
        mid = execute_insert('members', member_data)
        member_ids.append(mid)

    print(f"  ✅ 已生成 {len(member_ids)} 名学员")

    # ================================================================
    # 2. 公司情况
    # ================================================================
    print("正在生成公司信息...")
    companies_seen = set()
    for name in selected_names:
        member = execute_query("SELECT company_name FROM members WHERE name=?", (name,))
        if member and member[0]['company_name']:
            cname = member[0]['company_name']
            if cname not in companies_seen:
                companies_seen.add(cname)
                company_data = {
                    'name': cname,
                    'industry': random.choice(INDUSTRIES),
                    'scale': random.choice(['10-50人', '50-100人', '100-500人', '500人以上']),
                    'annual_revenue': random.choice(['1000万以下', '1000万-5000万', '5000万-1亿', '1亿以上']),
                    'founded_year': str(random.randint(2000, 2020)),
                    'city': random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都', '南京', '武汉']),
                }
                execute_insert('companies', company_data)

    print(f"  ✅ 已生成 {len(companies_seen)} 家公司信息")

    # ================================================================
    # 3. 小组学习会记录
    # ================================================================
    print("正在生成小组学习会记录...")
    group_count = 0
    for m in range(months):
        month_date = today - timedelta(days=30 * (months - 1 - m))
        # 每月2-4次学习会
        for _ in range(random.randint(2, 4)):
            session_date = month_date.replace(day=random.randint(5, 25))
            for mid in member_ids:
                # 75% 出勤率
                if random.random() < 0.75:
                    group_data = {
                        'member_id': mid,
                        'session_date': session_date.strftime('%Y-%m-%d'),
                        'theme': random.choice(SESSION_THEMES_GROUP),
                        'attendance': 'present',
                        'reflection': random.choice(['', '收获很大', '深有感触', '需要更多实践', '']),
                        'group_name': f"第{random.randint(1, 8)}小组",
                    }
                    execute_insert('group_sessions', group_data)
                    group_count += 1
                elif random.random() < 0.15:
                    # 请假
                    group_data = {
                        'member_id': mid,
                        'session_date': session_date.strftime('%Y-%m-%d'),
                        'theme': random.choice(SESSION_THEMES_GROUP),
                        'attendance': 'leave',
                        'group_name': f"第{random.randint(1, 8)}小组",
                    }
                    execute_insert('group_sessions', group_data)
                    group_count += 1

    print(f"  ✅ 已生成 {group_count} 条小组学习会记录")

    # ================================================================
    # 4. 班级学习会记录
    # ================================================================
    print("正在生成班级学习会记录...")
    class_count = 0
    for m in range(months):
        month_date = today - timedelta(days=30 * (months - 1 - m))
        # 每月1-2次班级会
        for _ in range(random.randint(1, 2)):
            session_date = month_date.replace(day=random.randint(10, 28))
            for mid in member_ids:
                if random.random() < 0.70:  # 70% 出勤率
                    role = 'participant'
                    if random.random() < 0.08:
                        role = 'speaker'
                    elif random.random() < 0.05:
                        role = 'organizer'

                    class_data = {
                        'member_id': mid,
                        'session_date': session_date.strftime('%Y-%m-%d'),
                        'theme': random.choice(SESSION_THEMES_CLASS),
                        'attendance': 'present',
                        'role': role,
                    }
                    execute_insert('class_sessions', class_data)
                    class_count += 1

    print(f"  ✅ 已生成 {class_count} 条班级学习会记录")

    # ================================================================
    # 5. 课程参与记录
    # ================================================================
    print("正在生成课程参与记录...")
    course_count = 0
    for m in range(months):
        month_date = today - timedelta(days=30 * (months - 1 - m))
        # 每2-3个月有一次课程
        if m % 2 == 0:
            course_date = month_date.replace(day=random.randint(15, 25))
            course_name = random.choice(COURSE_NAMES)
            for mid in member_ids:
                if random.random() < 0.65:  # 65% 出勤率
                    course_data = {
                        'member_id': mid,
                        'course_name': course_name,
                        'course_date': course_date.strftime('%Y-%m-%d'),
                        'attendance': 'present',
                        'score': round(random.uniform(60, 100), 1),
                        'evaluation': random.choice(['有收获', '非常好', '可以更好', '收获丰硕']),
                        'certificate': '是' if random.random() < 0.4 else '否',
                    }
                    execute_insert('courses', course_data)
                    course_count += 1

    print(f"  ✅ 已生成 {course_count} 条课程记录")

    # ================================================================
    # 6. 报告会参与记录
    # ================================================================
    print("正在生成报告会记录...")
    report_count = 0
    for m in range(months):
        if m % 3 == 0:  # 每季度一次报告会
            month_date = today - timedelta(days=30 * (months - 1 - m))
            meeting_date = month_date.replace(day=random.randint(1, 28))
            meeting_name = random.choice(MEETING_NAMES)
            for mid in member_ids:
                if random.random() < 0.55:  # 55% 出勤率
                    has_speech = 1 if random.random() < 0.15 else 0
                    report_data = {
                        'member_id': mid,
                        'meeting_name': meeting_name,
                        'meeting_date': meeting_date.strftime('%Y-%m-%d'),
                        'attendance': 'present',
                        'has_speech': has_speech,
                        'speech_topic': random.choice(['', '经营心得', '成长感悟', '企业变革']) if has_speech else '',
                    }
                    execute_insert('report_meetings', report_data)
                    report_count += 1

    print(f"  ✅ 已生成 {report_count} 条报告会记录")

    # ================================================================
    # 7. 游学参与记录
    # ================================================================
    print("正在生成游学记录...")
    tour_count = 0
    # 约30%的学员参加过游学
    for mid in member_ids[:int(len(member_ids) * 0.3)]:
        for _ in range(random.randint(1, 2)):
            tour_date = today - timedelta(days=random.randint(30, 365))
            tour_data = {
                'member_id': mid,
                'destination': random.choice(TOUR_DESTINATIONS),
                'tour_date': tour_date.strftime('%Y-%m-%d'),
                'duration_days': random.randint(3, 7),
                'harvest_score': random.randint(3, 5),
                'reflection': random.choice(['视野开阔', '深受启发', '收获良多', '需要消化吸收', '']),
            }
            execute_insert('study_tours', tour_data)
            tour_count += 1

    print(f"  ✅ 已生成 {tour_count} 条游学记录")

    # ================================================================
    # 8. 读书打卡记录
    # ================================================================
    print("正在生成读书打卡记录...")
    checkin_count = 0
    for mid in member_ids:
        # 60%的学员有打卡记录
        if random.random() < 0.6:
            # 每人10-60次打卡
            for _ in range(random.randint(10, 60)):
                checkin_date = today - timedelta(days=random.randint(0, 180))
                book = random.choice(BOOKS)
                checkin_data = {
                    'member_id': mid,
                    'checkin_date': checkin_date.strftime('%Y-%m-%d'),
                    'book_name': book,
                    'pages_read': random.randint(10, 50),
                    'duration_minutes': random.randint(20, 120),
                    'content_summary': random.choice([
                        '', '今日阅读收获很大', '对经营有了新认识',
                        '结合实践思考', '需要反复阅读',
                    ]),
                }
                execute_insert('reading_checkins', checkin_data)
                checkin_count += 1

    print(f"  ✅ 已生成 {checkin_count} 条读书打卡记录")

    # ================================================================
    # 9. 读书分享记录
    # ================================================================
    print("正在生成读书分享记录...")
    share_count = 0
    for mid in member_ids:
        # 40%的学员有分享记录
        if random.random() < 0.4:
            for _ in range(random.randint(1, 5)):
                share_date = today - timedelta(days=random.randint(0, 180))
                book = random.choice(BOOKS)
                share_data = {
                    'member_id': mid,
                    'share_date': share_date.strftime('%Y-%m-%d'),
                    'book_name': book,
                    'share_type': random.choice(['口头分享', '书面分享', '小组分享']),
                    'content': f"分享《{book}》的读后感：这本书对经营者的思维方式有很大启发...",
                    'quality_score': random.randint(3, 5),
                    'duration_minutes': random.randint(10, 45),
                }
                execute_insert('reading_shares', share_data)
                share_count += 1

    print(f"  ✅ 已生成 {share_count} 条读书分享记录")

    conn.close()

    # ================================================================
    # 总结
    # ================================================================
    print("\n" + "=" * 50)
    print("📊 模拟数据生成完成！")
    print("=" * 50)
    print(f"👤 学员: {len(member_ids)} 人")
    print(f"📅 覆盖周期: {months} 个月")
    print(f"📋 活动总记录: {group_count + class_count + course_count + report_count + tour_count + checkin_count + share_count} 条")
    print(f"   ├ 小组学习会: {group_count}")
    print(f"   ├ 班级学习会: {class_count}")
    print(f"   ├ 课程参与: {course_count}")
    print(f"   ├ 报告会参与: {report_count}")
    print(f"   ├ 游学参与: {tour_count}")
    print(f"   ├ 读书打卡: {checkin_count}")
    print(f"   └ 读书分享: {share_count}")
    print("=" * 50)
    print("\n运行 streamlit run app.py 启动系统查看效果！")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='生成盛和塾模拟数据')
    parser.add_argument('--members', type=int, default=50, help='学员数量')
    parser.add_argument('--months', type=int, default=6, help='数据覆盖月数')
    args = parser.parse_args()

    generate_sample_data(member_count=args.members, months=args.months)
