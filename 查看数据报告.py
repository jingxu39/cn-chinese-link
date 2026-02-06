"""
CN Chinese Link - 数据查看报告
一键运行，查看所有后端数据

使用方法：
1. 双击运行此文件
2. 或在命令行运行: python 查看数据报告.py
"""

import sqlite3
import os
from datetime import datetime

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "chinese_learning.db")

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def view_users(conn):
    """查看用户数据"""
    print_header("👥 用户列表 Users")

    cursor = conn.execute("""
        SELECT id, email, nickname, hsk_level, total_conversations, 
               total_words_learned, created_at, last_login 
        FROM users ORDER BY id
    """)
    users = cursor.fetchall()

    if not users:
        print("暂无用户注册")
        return

    print(f"\n总用户数: {len(users)} 人\n")
    print("-" * 60)

    for user in users:
        user_id, email, nickname, hsk_level, convs, words, created, last_login = user
        print(f"ID: {user_id}")
        print(f"  邮箱 Email: {email}")
        print(f"  昵称 Nickname: {nickname or '未设置'}")
        print(f"  HSK等级: {hsk_level or 3}")
        print(f"  对话数 Conversations: {convs or 0}")
        print(f"  学习生词数 Words: {words or 0}")
        print(f"  注册时间: {created}")
        print(f"  最后登录: {last_login or '从未登录'}")
        print("-" * 60)

def view_role_scene_stats(conn):
    """查看角色和场景统计 - 关键业务数据"""
    import json

    print_header("🎭 角色 & 场景统计 Role & Scene Analysis")

    cursor = conn.execute("""
        SELECT event_data FROM events 
        WHERE event_name = 'conversation_started' AND event_data IS NOT NULL
    """)
    rows = cursor.fetchall()

    if not rows:
        print("暂无对话数据")
        return

    # 统计角色、场景、HSK等级
    role_count = {}
    scene_count = {}
    hsk_count = {}
    role_scene_pairs = {}

    for row in rows:
        try:
            data = json.loads(row[0])
            role = data.get("role", "未知")
            scene = data.get("scene", "未知")
            hsk = data.get("hsk_level", 3)

            role_count[role] = role_count.get(role, 0) + 1
            scene_count[scene] = scene_count.get(scene, 0) + 1
            hsk_count[hsk] = hsk_count.get(hsk, 0) + 1

            pair = f"{role} + {scene}"
            role_scene_pairs[pair] = role_scene_pairs.get(pair, 0) + 1
        except:
            continue

    total_conversations = len(rows)

    print(f"\n📊 总对话次数: {total_conversations} 次\n")

    # 角色排名
    print("🏆 角色人气排名 (Most Popular Roles):")
    print("-" * 40)
    for i, (role, count) in enumerate(sorted(role_count.items(), key=lambda x: -x[1]), 1):
        percentage = count / total_conversations * 100
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"  {i}. {role}: {count}次 ({percentage:.1f}%) {bar}")

    print()

    # 场景排名
    print("🏆 场景人气排名 (Most Popular Scenes):")
    print("-" * 40)
    for i, (scene, count) in enumerate(sorted(scene_count.items(), key=lambda x: -x[1]), 1):
        percentage = count / total_conversations * 100
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"  {i}. {scene}: {count}次 ({percentage:.1f}%) {bar}")

    print()

    # HSK等级分布
    print("📈 用户HSK等级分布 (HSK Level Distribution):")
    print("-" * 40)
    for hsk in sorted(hsk_count.keys()):
        count = hsk_count[hsk]
        percentage = count / total_conversations * 100
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"  HSK {hsk}: {count}次 ({percentage:.1f}%) {bar}")

    print()

    # 角色+场景组合
    print("🔗 热门角色+场景组合 (Popular Combinations):")
    print("-" * 40)
    for i, (pair, count) in enumerate(sorted(role_scene_pairs.items(), key=lambda x: -x[1])[:5], 1):
        print(f"  {i}. {pair}: {count}次")


def view_events(conn):
    """查看埋点事件"""
    print_header("📊 埋点事件 Events (最近50条)")

    cursor = conn.execute("""
        SELECT e.id, e.user_id, u.email, e.event_name, e.event_data, e.created_at 
        FROM events e
        LEFT JOIN users u ON e.user_id = u.id
        ORDER BY e.id DESC LIMIT 50
    """)
    events = cursor.fetchall()

    if not events:
        print("暂无事件记录")
        return

    # 统计事件类型
    cursor2 = conn.execute("SELECT event_name, COUNT(*) FROM events GROUP BY event_name")
    event_stats = dict(cursor2.fetchall())

    print(f"\n总事件数: {sum(event_stats.values())} 条\n")
    print("事件类型统计:")
    for event_name, count in sorted(event_stats.items(), key=lambda x: -x[1]):
        print(f"  - {event_name}: {count} 次")

    print("\n" + "-" * 60)
    print("最近事件详情:\n")

    for event in events[:20]:  # 只显示最近20条详情
        event_id, user_id, email, event_name, event_data, created_at = event
        print(f"[{created_at}] {event_name}")
        print(f"  用户: {email or f'ID={user_id}' or '匿名'}")
        if event_data and event_data != '{}':
            print(f"  数据: {event_data}")
        print()

def view_vocab(conn):
    """查看生词本"""
    print_header("📚 生词本 Vocabulary")

    cursor = conn.execute("""
        SELECT v.id, v.user_id, u.email, v.word, v.meaning, v.mastered, v.created_at
        FROM vocab v
        LEFT JOIN users u ON v.user_id = u.id
        ORDER BY v.created_at DESC
    """)
    vocab = cursor.fetchall()

    if not vocab:
        print("暂无生词记录")
        return

    # 统计
    total = len(vocab)
    mastered = sum(1 for v in vocab if v[5] == 1)

    print(f"\n总生词数: {total} 个")
    print(f"已掌握: {mastered} 个")
    print(f"待学习: {total - mastered} 个")

    print("\n" + "-" * 60)
    print("生词列表:\n")

    for v in vocab:
        word_id, user_id, email, word, meaning, mastered_flag, created_at = v
        status = "✅已掌握" if mastered_flag else "📖待学习"
        print(f"{status} {word} - {meaning}")
        print(f"       用户: {email or f'ID={user_id}'} | 添加时间: {created_at}")
        print()

def view_summary(conn):
    """查看数据汇总"""
    print_header("📈 数据汇总 Summary")

    # 用户统计
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # 事件统计
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    # 生词统计
    vocab_total = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
    vocab_mastered = conn.execute("SELECT COUNT(*) FROM vocab WHERE mastered=1").fetchone()[0]

    # 今日活跃
    today = datetime.now().strftime("%Y-%m-%d")
    today_events = conn.execute(f"SELECT COUNT(*) FROM events WHERE created_at LIKE '{today}%'").fetchone()[0]

    print(f"""
┌─────────────────────────────────────┐
│  CN Chinese Link 数据报告            │
│  生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}       │
├─────────────────────────────────────┤
│  👥 注册用户数:     {user_count:>6} 人        │
│  📊 埋点事件总数:   {event_count:>6} 条        │
│  📚 生词总数:       {vocab_total:>6} 个        │
│  ✅ 已掌握生词:     {vocab_mastered:>6} 个        │
│  📅 今日事件数:     {today_events:>6} 条        │
└─────────────────────────────────────┘
""")

def main():
    """主函数"""
    print("\n" + "🇨🇳" * 20)
    print("\n   CN Chinese Link (中国缘) - 后端数据报告\n")
    print("🇨🇳" * 20)

    # 检查数据库是否存在
    if not os.path.exists(DB_PATH):
        print(f"\n❌ 数据库文件不存在: {DB_PATH}")
        print("请先运行应用并注册用户后再查看数据。")
        input("\n按回车键退出...")
        return

    # 连接数据库
    conn = sqlite3.connect(DB_PATH)

    try:
        # 显示汇总
        view_summary(conn)

        # 显示用户
        view_users(conn)

        # 显示角色和场景统计（关键业务数据）
        view_role_scene_stats(conn)

        # 显示生词
        view_vocab(conn)

        # 显示事件
        view_events(conn)

        print("\n" + "=" * 60)
        print("  报告生成完毕！")
        print("=" * 60)

    finally:
        conn.close()

    input("\n按回车键退出...")

if __name__ == "__main__":
    main()
