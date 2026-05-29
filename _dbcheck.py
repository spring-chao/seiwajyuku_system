from database import get_connection
conn = get_connection()
cur = conn.cursor()

# Check which members have activity records
cur.execute('''
    SELECT m.id, m.name, m.center, m.created_at,
           COALESCE(gs.c,0) as gss, COALESCE(cs.c,0) as css, 
           COALESCE(co.c,0) as coo, COALESCE(rm.c,0) as rmm,
           COALESCE(st.c,0) as stt, COALESCE(rc.c,0) as rcc, 
           COALESCE(rs.c,0) as rss
    FROM members m
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM group_sessions GROUP BY member_id) gs ON m.id=gs.member_id
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM class_sessions GROUP BY member_id) cs ON m.id=cs.member_id
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM courses GROUP BY member_id) co ON m.id=co.member_id
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM report_meetings GROUP BY member_id) rm ON m.id=rm.member_id
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM study_tours GROUP BY member_id) st ON m.id=st.member_id
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM reading_checkins GROUP BY member_id) rc ON m.id=rc.member_id
    LEFT JOIN (SELECT member_id,COUNT(*) as c FROM reading_shares GROUP BY member_id) rs ON m.id=rs.member_id
    ORDER BY m.id
''')
rows = cur.fetchall()

# Columns: id=0, name=1, center=2, created_at=3, gs=4, cs=5, co=6, rm=7, st=8, rc=9, rs=10
has_activity = [r for r in rows if any(r[i]>0 for i in range(4,11))]
print(f'有活动记录的学员: {len(has_activity)} 人')
print('他们的创建时间和姓名:')
for r in has_activity[:25]:
    total = sum(r[4:11])
    print(f'  id={r[0]:>4} | {r[1]:6s} | center={str(r[2] or "-"):10s} | created={r[3]} | 活动总数={total}')

print()
zero = [r for r in rows if all(r[i]==0 for i in range(4,11))]
print(f'无活动记录的学员: {len(zero)} 人 (共{len(rows)}人)')

conn.close()
