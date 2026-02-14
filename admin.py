"""
CN Chinese Link - 管理后台
密码保护的数据统计页面
"""

import streamlit as st
import sqlite3
import json
import os
from datetime import datetime

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chinese_learning.db")

def get_admin_password():
    """从 secrets 获取管理员密码"""
    try:
        return st.secrets.get("ADMIN_PASSWORD", "admin123")
    except:
        return "admin123"  # 默认密码，建议在 secrets 中配置

def check_password():
    """密码验证"""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if st.session_state.admin_authenticated:
        return True
    
    st.title("🔐 管理后台")
    st.warning("请输入管理员密码")
    
    password = st.text_input("密码", type="password")
    if st.button("登录"):
        if password == get_admin_password():
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("密码错误")
    return False

def get_db_connection():
    """获取数据库连接"""
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH)

def show_user_stats(conn):
    """显示用户统计"""
    st.header("👥 用户统计")
    
    cursor = conn.execute("""
        SELECT id, email, nickname, hsk_level, total_conversations, 
               total_words_learned, created_at, last_login 
        FROM users ORDER BY id DESC
    """)
    users = cursor.fetchall()
    
    if not users:
        st.info("暂无用户注册")
        return
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总用户数", len(users))
    
    # 活跃用户（最近7天登录）
    active_count = sum(1 for u in users if u[7] and "2026-02" in str(u[7]))
    col2.metric("本月活跃", active_count)
    
    # 总对话数
    total_convs = sum(u[4] or 0 for u in users)
    col3.metric("总对话数", total_convs)
    
    st.subheader("用户列表")
    
    # 转换为表格显示
    user_data = []
    for user in users:
        user_data.append({
            "ID": user[0],
            "邮箱": user[1],
            "昵称": user[2] or "-",
            "HSK": user[3] or 3,
            "对话数": user[4] or 0,
            "生词数": user[5] or 0,
            "注册时间": user[6],
            "最后登录": user[7] or "-"
        })
    
    st.dataframe(user_data, use_container_width=True)

def show_role_scene_stats(conn):
    """显示角色和场景统计"""
    st.header("🎭 角色 & 场景统计")
    
    cursor = conn.execute("""
        SELECT event_data FROM events 
        WHERE event_name = 'conversation_started' AND event_data IS NOT NULL
    """)
    rows = cursor.fetchall()
    
    if not rows:
        st.info("暂无对话数据")
        return
    
    # 统计
    role_count = {}
    scene_count = {}
    hsk_count = {}
    
    for row in rows:
        try:
            data = json.loads(row[0])
            role = data.get("role", "未知")
            scene = data.get("scene", "未知")
            hsk = data.get("hsk_level", 3)
            
            role_count[role] = role_count.get(role, 0) + 1
            scene_count[scene] = scene_count.get(scene, 0) + 1
            hsk_count[hsk] = hsk_count.get(hsk, 0) + 1
        except:
            continue
    
    total = len(rows)
    st.metric("总对话次数", f"{total} 次")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 角色人气排名")
        for role, count in sorted(role_count.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            st.write(f"**{role}**: {count}次 ({pct:.1f}%)")
            st.progress(pct / 100)
    
    with col2:
        st.subheader("🏆 场景人气排名")
        for scene, count in sorted(scene_count.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            st.write(f"**{scene}**: {count}次 ({pct:.1f}%)")
            st.progress(pct / 100)
    
    st.subheader("📈 HSK等级分布")
    hsk_data = {f"HSK {k}": v for k, v in sorted(hsk_count.items())}
    st.bar_chart(hsk_data)

def show_vocab_stats(conn):
    """显示生词本统计"""
    st.header("📚 生词本统计")
    
    cursor = conn.execute("""
        SELECT v.word, v.meaning, v.mastered, u.email, v.created_at
        FROM vocab v
        LEFT JOIN users u ON v.user_id = u.id
        ORDER BY v.created_at DESC
    """)
    vocab = cursor.fetchall()
    
    if not vocab:
        st.info("暂无生词记录")
        return
    
    total = len(vocab)
    mastered = sum(1 for v in vocab if v[2] == 1)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总生词数", total)
    col2.metric("已掌握", mastered)
    col3.metric("待学习", total - mastered)
    
    st.subheader("生词列表")
    vocab_data = []
    for v in vocab[:50]:  # 只显示最近50个
        vocab_data.append({
            "状态": "✅" if v[2] else "📖",
            "单词": v[0],
            "释义": v[1],
            "用户": v[3] or "-",
            "添加时间": v[4]
        })
    st.dataframe(vocab_data, use_container_width=True)

def show_events(conn):
    """显示埋点事件"""
    st.header("📊 埋点事件")
    
    # 事件类型统计
    cursor = conn.execute("SELECT event_name, COUNT(*) FROM events GROUP BY event_name")
    event_stats = dict(cursor.fetchall())
    
    if not event_stats:
        st.info("暂无事件记录")
        return
    
    st.metric("总事件数", sum(event_stats.values()))
    
    st.subheader("事件类型分布")
    st.bar_chart(event_stats)
    
    # 最近事件
    st.subheader("最近事件 (20条)")
    cursor = conn.execute("""
        SELECT e.event_name, u.email, e.event_data, e.created_at 
        FROM events e
        LEFT JOIN users u ON e.user_id = u.id
        ORDER BY e.id DESC LIMIT 20
    """)
    events = cursor.fetchall()
    
    event_data = []
    for e in events:
        event_data.append({
            "时间": e[3],
            "事件": e[0],
            "用户": e[1] or "匿名",
            "数据": e[2] if e[2] != '{}' else "-"
        })
    st.dataframe(event_data, use_container_width=True)

def main():
    st.set_page_config(page_title="管理后台", page_icon="🔐", layout="wide")
    
    # 密码验证
    if not check_password():
        return
    
    # 已验证，显示管理界面
    st.title("🔐 CN Chinese Link 管理后台")
    
    # 登出按钮
    if st.sidebar.button("🚪 退出登录"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # 检查数据库
    conn = get_db_connection()
    if not conn:
        st.error(f"数据库文件不存在: {DB_PATH}")
        return
    
    # 标签页
    tab1, tab2, tab3, tab4 = st.tabs(["👥 用户", "🎭 角色场景", "📚 生词本", "📊 事件"])
    
    with tab1:
        show_user_stats(conn)
    
    with tab2:
        show_role_scene_stats(conn)
    
    with tab3:
        show_vocab_stats(conn)
    
    with tab4:
        show_events(conn)
    
    conn.close()

if __name__ == "__main__":
    main()
