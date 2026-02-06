"""
CN Chinese Link (中国缘) - AI 沉浸式中文学习应用
v1.2 版本 - 用户登录 + 数据存储
- 支持邮箱注册/登录
- 用户数据云端存储
- 学习进度追踪
"""

import streamlit as st
import sqlite3
import json
import os
import tempfile
import time
import base64
import hashlib
from datetime import datetime
from openai import OpenAI
import dashscope
from dashscope.audio.tts import SpeechSynthesizer

# 尝试导入语音录制组件
try:
    from streamlit_mic_recorder import mic_recorder
    HAS_MIC_RECORDER = True
except ImportError:
    HAS_MIC_RECORDER = False

# ============================================================
# API 配置 - 安全方式：从 Streamlit Secrets 读取
# ============================================================
# 本地开发：在 .streamlit/secrets.toml 中配置
# 云端部署：在 Streamlit Cloud 的 Settings > Secrets 中配置

def get_api_key(key_name, default=""):
    """安全获取 API Key"""
    try:
        return st.secrets.get(key_name, default)
    except:
        return default

DEEPSEEK_API_KEY = get_api_key("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DASHSCOPE_API_KEY = get_api_key("DASHSCOPE_API_KEY")
dashscope.api_key = DASHSCOPE_API_KEY

DB_PATH = "chinese_learning.db"

# ============================================================
# 密码加密函数
# ============================================================
def hash_password(password):
    """简单的密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """验证密码"""
    return hash_password(password) == hashed

# ============================================================
# 角色定义 - 包含语音配置
# ============================================================
ROLES = {
    "王阿姨": {
        "title": "丈母娘/婆婆",
        "title_en": "Mother-in-law",
        "avatar": "👵",
        "description": "热情关心的长辈",
        "description_en": "A warm and caring elder",
        "personality": "热情、关心、爱唠叨",
        "scenes": ["春节回家", "催婚/催生", "饭桌礼仪"],
        "scenes_en": ["Spring Festival Visit", "Marriage Pressure", "Table Manners"],
        "gender": "female",
        "voice": "sambert-zhichu-emo-v1",
        "voice_style": "warm"
    },
    "张总": {
        "title": "商业老板",
        "title_en": "Business Boss",
        "avatar": "👔",
        "description": "精明干练的商业人士",
        "description_en": "A shrewd businessman",
        "personality": "精明、严肃、讲究效率",
        "scenes": ["项目汇报", "商务宴请", "薪资谈判"],
        "scenes_en": ["Project Report", "Business Dinner", "Salary Negotiation"],
        "gender": "male",
        "voice": "sambert-zhiwei-emo-v1",
        "voice_style": "professional"
    },
    "小李": {
        "title": "中国朋友",
        "title_en": "Chinese Friend",
        "avatar": "🧑",
        "description": "年轻活泼的朋友",
        "description_en": "A young and energetic friend",
        "personality": "活泼、幽默、爱分享",
        "scenes": ["周末约饭", "吐槽工作", "聊网络热梗"],
        "scenes_en": ["Weekend Hangout", "Work Complaints", "Internet Trends"],
        "gender": "male",
        "voice": "sambert-zhijia-emo-v1",
        "voice_style": "casual"
    },
    "服务员": {
        "title": "餐厅/商店服务员",
        "title_en": "Waiter/Shop Staff",
        "avatar": "🧑‍🍳",
        "description": "热情周到的服务人员",
        "description_en": "Friendly service staff",
        "personality": "礼貌、热情、专业",
        "scenes": ["餐厅点餐", "商场买衣服", "咖啡店点单"],
        "scenes_en": ["Restaurant Ordering", "Clothes Shopping", "Coffee Shop"],
        "gender": "female",
        "voice": "sambert-zhimiao-emo-v1",
        "voice_style": "polite"
    },
    "陈老师": {
        "title": "中文老师",
        "title_en": "Chinese Teacher",
        "avatar": "👩‍🏫",
        "description": "耐心细致的中文老师",
        "description_en": "A patient Chinese teacher",
        "personality": "耐心、专业、鼓励式教学",
        "scenes": ["作业辅导", "考试咨询", "留学建议"],
        "scenes_en": ["Homework Help", "Exam Consultation", "Study Abroad Advice"],
        "gender": "female",
        "voice": "sambert-zhimiao-emo-v1",
        "voice_style": "patient"
    },
    "赵姐": {
        "title": "职场同事",
        "title_en": "Office Colleague",
        "avatar": "👩‍💼",
        "description": "职场老油条",
        "description_en": "An experienced colleague",
        "personality": "热情、八卦、懂人情世故",
        "scenes": ["点奶茶", "八卦聊天", "工作协作"],
        "scenes_en": ["Ordering Milk Tea", "Office Gossip", "Work Collaboration"],
        "gender": "female",
        "voice": "sambert-zhiyan-emo-v1",
        "voice_style": "lively"
    }
}

# ============================================================
# 多音字词典 - 用于纠正常见多音字
# ============================================================
POLYPHONE_DICT = {
    # 常见多音字及其正确读音（使用SSML phoneme标注）
    "行": {"银行": "háng", "行走": "xíng", "行业": "háng", "行为": "xíng", "行李": "xíng"},
    "长": {"长大": "zhǎng", "长度": "cháng", "长辈": "zhǎng", "长江": "cháng", "成长": "zhǎng"},
    "了": {"了解": "liǎo", "好了": "le", "完了": "le", "为了": "le", "了不起": "liǎo"},
    "得": {"得到": "dé", "跑得快": "de", "觉得": "de", "得了": "dé", "取得": "dé"},
    "地": {"地方": "dì", "慢慢地": "de", "地球": "dì", "土地": "dì"},
    "还": {"还是": "hái", "还给": "huán", "还有": "hái", "归还": "huán"},
    "觉": {"觉得": "jué", "睡觉": "jiào", "感觉": "jué", "午觉": "jiào"},
    "教": {"教室": "jiào", "教书": "jiāo", "教育": "jiào", "教学": "jiāo"},
    "乐": {"快乐": "lè", "音乐": "yuè", "乐趣": "lè", "乐器": "yuè"},
    "难": {"难题": "nán", "困难": "nán", "难民": "nàn", "灾难": "nàn"},
    "发": {"发现": "fā", "头发": "fà", "发展": "fā", "理发": "fà"},
    "数": {"数学": "shù", "数数": "shǔ", "数字": "shù", "数一数": "shǔ"},
    "重": {"重要": "zhòng", "重复": "chóng", "重量": "zhòng", "重新": "chóng"},
    "干": {"干净": "gān", "干活": "gàn", "干部": "gàn", "干燥": "gān"},
    "少": {"多少": "shǎo", "少年": "shào", "少数": "shǎo", "少女": "shào"},
    "好": {"好吃": "hǎo", "爱好": "hào", "好人": "hǎo", "好奇": "hào"},
    "分": {"分钟": "fēn", "分数": "fēn", "身分": "fèn", "成分": "fèn"},
    "便": {"方便": "biàn", "便宜": "pián", "便利": "biàn", "大便": "biàn"},
    "看": {"看见": "kàn", "看守": "kān", "看病": "kàn", "看护": "kān"},
    "调": {"调查": "diào", "空调": "tiáo", "调整": "tiáo", "调动": "diào"},
}

HSK_LEVELS = {1: "HSK 1 - 初级入门", 2: "HSK 2 - 基础对话", 3: "HSK 3 - 日常交流", 4: "HSK 4 - 中级流利", 5: "HSK 5 - 高级应用", 6: "HSK 6 - 精通掌握"}

# ============================================================
# 数据库
# ============================================================
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT,
        hsk_level INTEGER DEFAULT 3,
        total_conversations INTEGER DEFAULT 0,
        total_words_learned INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )""")

    # 对话历史表（关联用户）
    cursor.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        scene TEXT,
        sender TEXT,
        content TEXT,
        pinyin TEXT,
        english TEXT,
        keywords TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # 生词本（关联用户）
    cursor.execute("""CREATE TABLE IF NOT EXISTS vocab (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        word TEXT,
        meaning TEXT,
        context TEXT,
        mastered INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, word)
    )""")

    # 埋点事件表
    cursor.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_name TEXT,
        event_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    conn.commit()
    conn.close()

# ============================================================
# 用户认证函数
# ============================================================
def register_user(email, password, nickname=None):
    """注册新用户"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nickname) VALUES (?, ?, ?)",
            (email.lower(), password_hash, nickname or email.split('@')[0])
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "该邮箱已被注册 Email already registered"}
    finally:
        conn.close()

def login_user(email, password):
    """用户登录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, nickname, hsk_level FROM users WHERE email = ?", (email.lower(),))
    result = cursor.fetchone()

    if result and verify_password(password, result[1]):
        # 更新最后登录时间
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now(), result[0]))
        conn.commit()
        conn.close()
        return {"success": True, "user_id": result[0], "nickname": result[2], "hsk_level": result[3]}

    conn.close()
    return {"success": False, "error": "邮箱或密码错误 Invalid email or password"}

def get_user_info(user_id):
    """获取用户信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, nickname, hsk_level, total_conversations, total_words_learned, created_at FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "id": result[0], "email": result[1], "nickname": result[2],
            "hsk_level": result[3], "total_conversations": result[4],
            "total_words_learned": result[5], "created_at": result[6]
        }
    return None

def update_user_stats(user_id, conversations_delta=0, words_delta=0):
    """更新用户统计"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET total_conversations = total_conversations + ?, total_words_learned = total_words_learned + ? WHERE id = ?",
        (conversations_delta, words_delta, user_id)
    )
    conn.commit()
    conn.close()

# ============================================================
# 埋点函数
# ============================================================
def track_event(event_name, event_data=None):
    """记录用户行为事件"""
    user_id = st.session_state.get("user_id")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (user_id, event_name, event_data) VALUES (?, ?, ?)",
        (user_id, event_name, json.dumps(event_data or {}))
    )
    conn.commit()
    conn.close()

# ============================================================
# 生词本函数（带用户ID）
# ============================================================
def save_word_to_vocab(word, meaning, context=""):
    user_id = st.session_state.get("user_id")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO vocab (user_id, word, meaning, context, mastered) VALUES (?, ?, ?, ?, 0)", (user_id, word, meaning, context))
        conn.commit()
        # 更新用户统计
        if user_id:
            update_user_stats(user_id, words_delta=1)
        # 埋点
        track_event("word_saved", {"word": word})
        return True
    except:
        return False
    finally:
        conn.close()

def get_all_vocab():
    user_id = st.session_state.get("user_id")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT id, word, meaning, context, created_at FROM vocab WHERE user_id = ? AND mastered = 0 ORDER BY created_at DESC", (user_id,))
    else:
        cursor.execute("SELECT id, word, meaning, context, created_at FROM vocab WHERE mastered = 0 ORDER BY created_at DESC")
    results = cursor.fetchall()
    conn.close()
    return results

def mark_word_mastered(word_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE vocab SET mastered = 1 WHERE id = ?", (word_id,))
    conn.commit()
    conn.close()
    # 埋点
    track_event("word_mastered", {"word_id": word_id})

def delete_word(word_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vocab WHERE id = ?", (word_id,))
    conn.commit()
    conn.close()

# ============================================================
# DeepSeek LLM
# ============================================================
def get_deepseek_response(messages, role_name, scene, hsk_level):
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=30.0)
        role_info = ROLES[role_name]

        system_prompt = f"""你是中文学习应用中的虚拟角色。
角色: {role_name} ({role_info['title']})
性格: {role_info['personality']}
场景: {scene}
学生水平: HSK {hsk_level}

回复规则:
1. 沉浸角色，用符合身份的语气说话
2. 根据HSK{hsk_level}级调整用语难度
3. 回复简洁自然(1-3句话)

输出JSON格式:
{{"chinese": "中文回复", "pinyin": "拼音", "english": "英文翻译", "keywords": [{{"word": "生词", "meaning": "释义"}}], "suggestions": ["回复选项1", "回复选项2", "回复选项3"]}}

只返回JSON！"""

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        with st.spinner(f"⏳ {role_name} 正在思考..."):
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=full_messages,
                temperature=0.8,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

        result = json.loads(response.choices[0].message.content)

        for field in ["chinese", "pinyin", "english", "keywords", "suggestions"]:
            if field not in result:
                result[field] = "" if field in ["chinese", "pinyin", "english"] else []
        return result
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON解析错误: {e}")
        return {"chinese": "抱歉，我没听清，请再说一遍。", "pinyin": "bào qiàn, wǒ méi tīng qīng", "english": "Sorry, I didn't catch that.", "keywords": [], "suggestions": ["请再说一遍", "好的"]}
    except Exception as e:
        st.error(f"❌ DeepSeek API 错误: {str(e)}")
        st.info("💡 提示：请检查网络连接，或稍后重试")
        return None

# ============================================================
# TTS 语音合成 - 根据角色性别选择音色
# ============================================================
def text_to_speech_ali(text, role_name=None):
    """
    语音合成 - 根据角色性别选择音色

    可用音色：
    - 女声: sambert-zhimiao-emo-v1 (旧API)
    - 男声: longanyang (CosyVoice v3)
    """
    try:
        # 从角色配置中获取性别
        is_male = False
        if role_name and role_name in ROLES:
            is_male = ROLES[role_name].get("gender") == "male"

        if is_male:
            # 男声使用 CosyVoice v3
            try:
                from dashscope.audio.tts_v2 import SpeechSynthesizer as SpeechSynthesizerV2
                from dashscope.audio.tts_v2 import AudioFormat

                synthesizer = SpeechSynthesizerV2(
                    model="cosyvoice-v3-flash",
                    voice="longanyang",
                    format=AudioFormat.MP3_22050HZ_MONO_256KBPS
                )
                audio = synthesizer.call(text)

                if audio and len(audio) > 0:
                    return audio
            except Exception as e:
                st.warning(f"男声合成失败: {e}，使用备用女声")

        # 女声或备用：使用 sambert
        result = SpeechSynthesizer.call(
            model='sambert-zhimiao-emo-v1',
            text=text,
            sample_rate=16000,
            format='mp3'
        )
        audio_data = result.get_audio_data()
        if audio_data and len(audio_data) > 0:
            return audio_data

        st.error("语音合成失败")
        return None

    except Exception as e:
        st.error(f"语音合成错误: {str(e)}")
        return None

# ============================================================
# ASR 语音识别 - 使用 paraformer-realtime-v2（非流式）
# ============================================================
def convert_to_wav(audio_bytes):
    """将音频转换为 WAV 格式 (16kHz/mono/16bit)"""
    try:
        # 配置 ffmpeg 路径
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
        except:
            pass

        from pydub import AudioSegment
        import io

        # 尝试读取音频
        try:
            if audio_bytes[:4] == b'RIFF':
                audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
            else:
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        except Exception as e:
            st.warning(f"音频读取失败: {e}")
            return None

        # 转换为 16kHz 单声道 16bit
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

        # 导出为 WAV
        output = io.BytesIO()
        audio.export(output, format="wav")
        return output.getvalue()
    except Exception as e:
        st.warning(f"音频转换失败: {e}")
        return None

def speech_to_text_ali(audio_bytes):
    """使用阿里百炼 Paraformer 进行语音识别（非流式：录完一段再识别）"""
    try:
        from http import HTTPStatus
        from dashscope.audio.asr import Recognition

        # 1) 检查是否已经是 WAV 格式
        is_wav = audio_bytes[:4] == b'RIFF'

        if is_wav:
            # 已经是 WAV，尝试标准化
            converted = convert_to_wav(audio_bytes)
            if converted:
                audio_bytes = converted
        else:
            # 不是 WAV，需要转换
            converted = convert_to_wav(audio_bytes)
            if not converted:
                st.error("❌ 音频处理失败，请重试")
                return None
            audio_bytes = converted

        # 2) 写临时 wav 文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", mode='wb') as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            # 3) 非流式调用（最稳定）
            recognition = Recognition(
                model="paraformer-realtime-v2",
                format="wav",
                sample_rate=16000,
                language_hints=["zh", "en"],
                callback=None  # 非流式，不需要回调
            )
            result = recognition.call(temp_path)

            if result.status_code != HTTPStatus.OK:
                st.error("❌ 语音识别失败，请重试")
                return None

            # 4) 获取识别结果 - get_sentence() 可能返回 list 或 dict
            sentence = result.get_sentence()

            text = ""
            if sentence:
                if isinstance(sentence, list):
                    # 如果是列表，提取所有句子的文本
                    texts = []
                    for s in sentence:
                        if isinstance(s, dict) and s.get('text'):
                            texts.append(s['text'])
                    text = ' '.join(texts)
                elif isinstance(sentence, dict):
                    # 如果是字典，直接获取 text
                    text = sentence.get('text', '')
                elif isinstance(sentence, str):
                    text = sentence

            text = text.strip()

            if not text:
                st.warning("🔇 未检测到语音，请说话清晰一些")
                return None

            return text

        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        st.error("❌ 语音识别出错，请重试")
        return None

# ============================================================
# 样式
# ============================================================
def apply_styles():
    st.markdown("""<style>
    /* 全局字体与背景 - 使用系统字体加速加载 */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(180deg, #fdfbf7 0%, #f4f7f6 100%);
    }

    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    
    /* 按钮样式优化 */
    .stButton > button {
        width: 100%; 
        padding: 0.6rem 0.5rem; 
        font-size: 1rem; 
        font-weight: 500;
        border-radius: 12px; 
        min-height: 48px;
        border: none;
        transition: transform 0.1s, box-shadow 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    .stButton > button:active {
        transform: scale(0.98);
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* 主要操作按钮颜色 */
    button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    /* 聊天气泡优化 */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 15px;
        padding-bottom: 20px;
    }

    .chat-ai {
        background: white;
        padding: 18px;
        border-radius: 4px 18px 18px 18px;
        margin: 10px 0;
        max-width: 92%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef0f2;
        position: relative;
    }
    
    .chat-ai::before {
        content: "AI";
        position: absolute;
        top: -10px;
        left: 0;
        font-size: 0.7rem;
        background: #eef0f2;
        padding: 2px 6px;
        border-radius: 4px;
        color: #666;
    }

    .chat-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 18px 18px 4px 18px;
        margin: 10px 0 10px auto;
        max-width: 85%;
        text-align: right;
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
    }

    .chinese-text {
        font-size: 1.4rem;
        font-weight: 600;
        color: #2c3e50;
        line-height: 1.6;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    .pinyin-text {
        font-size: 0.9rem;
        color: #7f8c8d;
        font-family: 'Courier New', monospace; /* 等宽字体对齐拼音 */
        margin-bottom: 4px;
    }

    .english-text {
        font-size: 0.95rem;
        color: #555;
        margin-top: 12px;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 8px;
        border-left: 3px solid #667eea;
    }

    /* 角色选择卡片 */
    .role-card {
        background: white;
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        transition: transform 0.2s;
        border: 2px solid transparent;
        cursor: pointer;
    }
    
    .role-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    
    /* 首页样式 */
    .landing-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .landing-subtitle {
        font-size: 1.1rem;
        color: #7f8c8d;
        text-align: center; 
        font-weight: 300;
        letter-spacing: 1px;
        margin-bottom: 2rem;
    }

    /* 生词本卡片 */
    .vocab-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        margin: 12px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid #667eea;
        position: relative;
        transition: transform 0.2s;
    }
    
    .vocab-card:hover {
        transform: scale(1.01);
    }

    /* 场景头部 */
    .scene-header {
        background: linear-gradient(135deg, #6b8cce 0%, #56338a 100%);
        color: white;
        padding: 16px 20px;
        border-radius: 16px;
        margin-bottom: 25px;
        box-shadow: 0 6px 15px rgba(86, 51, 138, 0.25);
        display: flex;
        align-items: center;
        width: 100%;
    }
    
    .input-container {
        background: white;
        border-radius: 20px;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.05);
        position: sticky;
        bottom: 0;
        z-index: 100;
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    </style>""", unsafe_allow_html=True)

# ============================================================
# 页面
# ============================================================
def render_auth():
    """登录/注册页面"""
    st.markdown("""
    <div style="text-align: center; padding: 30px 20px;">
        <div style="font-size: 3rem; margin-bottom: 15px;">🇨🇳</div>
        <h1 style="font-size: 2rem; font-weight: 700; color: #667eea; margin-bottom: 5px;">中国缘</h1>
        <p style="color: #888; font-size: 0.85rem;">CN Chinese Link</p>
    </div>
    """, unsafe_allow_html=True)

    # 切换登录/注册
    auth_mode = st.radio("", ["登录 Login", "注册 Register"], horizontal=True, label_visibility="collapsed")

    st.markdown("---")

    if auth_mode == "登录 Login":
        st.markdown("### 👋 欢迎回来 Welcome Back")
        with st.form("login_form"):
            email = st.text_input("📧 邮箱 Email", placeholder="your@email.com")
            password = st.text_input("🔒 密码 Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("登录 Login", type="primary", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("请填写邮箱和密码 Please fill in email and password")
                else:
                    result = login_user(email, password)
                    if result["success"]:
                        st.session_state.user_id = result["user_id"]
                        st.session_state.nickname = result["nickname"]
                        st.session_state.user_hsk_level = result["hsk_level"]
                        st.session_state.logged_in = True
                        # 埋点
                        track_event("user_login", {"email": email})
                        st.success("✅ 登录成功 Login successful!")
                        time.sleep(0.5)
                        st.session_state.page = "landing"
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")

    else:  # 注册
        st.markdown("### 🎉 创建账户 Create Account")
        with st.form("register_form"):
            email = st.text_input("📧 邮箱 Email", placeholder="your@email.com")
            nickname = st.text_input("👤 昵称 Nickname (可选 Optional)", placeholder="Your name")
            password = st.text_input("🔒 密码 Password", type="password", placeholder="At least 6 characters")
            password2 = st.text_input("🔒 确认密码 Confirm Password", type="password", placeholder="Re-enter password")
            submit = st.form_submit_button("注册 Register", type="primary", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("请填写邮箱和密码 Please fill in email and password")
                elif len(password) < 6:
                    st.error("密码至少6位 Password must be at least 6 characters")
                elif password != password2:
                    st.error("两次密码不一致 Passwords do not match")
                elif "@" not in email:
                    st.error("请输入有效邮箱 Please enter a valid email")
                else:
                    result = register_user(email, password, nickname)
                    if result["success"]:
                        st.session_state.user_id = result["user_id"]
                        st.session_state.nickname = nickname or email.split('@')[0]
                        st.session_state.logged_in = True
                        # 埋点
                        track_event("user_register", {"email": email})
                        st.success("✅ 注册成功 Registration successful!")
                        time.sleep(0.5)
                        st.session_state.page = "landing"
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")

    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #999; font-size: 0.8rem;'>v1.2 · 数据安全存储 Secure Data Storage</p>", unsafe_allow_html=True)


def render_landing():
    # 检查是否已登录
    if not st.session_state.get("logged_in"):
        render_auth()
        return

    # 已登录用户显示欢迎页
    nickname = st.session_state.get("nickname", "学习者")

    st.markdown(f"""
    <div style="text-align: center; padding: 50px 20px;">
        <div style="font-size: 4rem; margin-bottom: 20px;">🇨🇳</div>
        <h1 style="font-size: 2.5rem; font-weight: 700; color: #667eea; margin-bottom: 10px;">中国缘</h1>
        <p style="color: #888; font-size: 0.9rem; margin-bottom: 5px;">CN Chinese Link</p>
        <p style="color: #666; font-size: 1rem; margin-bottom: 20px;">遇见你的中国家人和朋友<br><span style="font-size: 0.9rem;">Meet Your Chinese Family & Friends</span></p>
        <p style="color: #667eea; font-size: 1.1rem;">👋 你好，{nickname}！</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        if st.button("🚀 开始学习 Start Learning", type="primary", use_container_width=True):
            # 埋点
            track_event("start_learning")
            st.session_state.page = "select"
            st.rerun()

    st.markdown("<div style='text-align: center; margin-top: 50px; color: #ccc; font-size: 0.8rem;'>v1.1</div>", unsafe_allow_html=True)

def render_selection():
    st.markdown("<h2 style='text-align: center; color: #333; margin-bottom: 20px;'>🎭 选择你的语伴 Choose Your Partner</h2>", unsafe_allow_html=True)

    role_options = list(ROLES.keys())

    # 简化的角色选择 - 更快加载
    for i, role_name in enumerate(role_options):
        role = ROLES[role_name]
        gender_icon = "👨" if role["gender"] == "male" else "👩"
        title_en = role.get("title_en", "")

        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"<div style='font-size: 2.5rem; text-align: center;'>{role['avatar']}</div>", unsafe_allow_html=True)
        with col2:
            if st.button(f"{role_name} ({title_en}) {gender_icon}", key=f"btn_role_{i}", use_container_width=True):
                st.session_state.selected_role = role_name
                st.rerun()

    if st.session_state.get("selected_role"):
        selected_role = st.session_state.selected_role
        role = ROLES[selected_role]
        title_en = role.get("title_en", "")
        description_en = role.get("description_en", "")

        st.markdown("---")
        st.success(f"✅ 已选择 Selected：{role['avatar']} {selected_role} ({title_en})")

        st.markdown("**📍 选择场景 Choose Scene**")
        # 创建带英文的场景选项
        scenes = role["scenes"]
        scenes_en = role.get("scenes_en", scenes)
        scene_options = [f"{scenes[i]} ({scenes_en[i]})" for i in range(len(scenes))]
        selected_scene_display = st.selectbox("场景 Scene：", scene_options, label_visibility="collapsed")
        # 提取中文场景名
        selected_scene = scenes[scene_options.index(selected_scene_display)]

        st.markdown("**📊 中文水平 Chinese Level**")
        hsk_level = st.select_slider("HSK等级 Level：", options=[1, 2, 3, 4, 5, 6], value=3, format_func=lambda x: f"HSK {x}")

        st.markdown("---")
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("⬅️ 返回 Back", use_container_width=True):
                st.session_state.page = "landing"
                st.session_state.selected_role = None
                st.rerun()
        with col2:
            if st.button("💬 开始对话 Start Chat", type="primary", use_container_width=True):
                st.session_state.selected_scene = selected_scene
                st.session_state.hsk_level = hsk_level
                st.session_state.messages = []
                st.session_state.page = "chat"
                # 埋点：开始对话
                track_event("conversation_started", {"role": selected_role, "scene": selected_scene, "hsk_level": hsk_level})
                st.rerun()

def render_chat():
    role_name = st.session_state.get("selected_role")
    scene = st.session_state.get("selected_scene")
    hsk_level = st.session_state.get("hsk_level", 3)

    if not role_name or not scene:
        st.session_state.page = "select"
        st.rerun()
        return

    role_info = ROLES[role_name]
    gender_text = "男声" if role_info["gender"] == "male" else "女声"

    st.markdown(f'<div class="scene-header"><span style="font-size: 2rem;">{role_info["avatar"]}</span> <strong>{role_name} · {scene}</strong> <span style="font-size: 0.85rem;">HSK {hsk_level} | 🔊{gender_text}</span></div>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # AI开场 - 显示加载提示
    if len(st.session_state.messages) == 0:
        st.markdown("""
        <div style="text-align: center; padding: 40px; color: #666;">
            <div style="font-size: 2rem; margin-bottom: 15px;">💬</div>
            <div>正在准备对话...<br><span style="font-size: 0.9rem; color: #999;">Preparing conversation...</span></div>
        </div>
        """, unsafe_allow_html=True)

        opening = [{"role": "user", "content": f"（场景开始：{scene}）请你作为{role_name}先开口说第一句话。"}]
        response = get_deepseek_response(opening, role_name, scene, hsk_level)
        if response:
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    # 显示对话
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "assistant":
            render_ai_message(msg["content"], i, role_name)
        else:
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 推荐回复
    suggestions = []
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        last = st.session_state.messages[-1]["content"]
        if isinstance(last, dict):
            suggestions = last.get("suggestions", [])

    if suggestions:
        st.markdown("**💡 推荐回复 Suggested Replies：**")
        cols = st.columns(len(suggestions))
        for idx, sug in enumerate(suggestions):
            with cols[idx]:
                if st.button(f"💬 {sug}", key=f"sug_{len(st.session_state.messages)}_{idx}", use_container_width=True):
                    process_input(sug, role_name, scene, hsk_level)

    # ============================================================
    # 输入区域 - 文字 + 语音
    # ============================================================
    st.markdown("---")
    st.markdown("**💬 回复方式 Reply Options：**")

    # 文字输入
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("输入中文 Type Chinese", placeholder="用中文回复... Type in Chinese...", label_visibility="collapsed")
        col1, col2 = st.columns([3, 1])
        with col2:
            submit = st.form_submit_button("发送 Send 📤", use_container_width=True)
        if submit and user_input.strip():
            process_input(user_input.strip(), role_name, scene, hsk_level)

    # 语音输入
    if HAS_MIC_RECORDER:
        st.markdown("**🎤 或语音输入 Or Voice Input：**")

        try:
            from streamlit_mic_recorder import mic_recorder
            audio = mic_recorder(
                start_prompt="🎤 录音 Record",
                stop_prompt="⏹️ 停止 Stop",
                just_once=False,
                use_container_width=True,
                format="wav",
                key=f"mic_recorder_{len(st.session_state.messages)}"
            )

            if audio is not None:
                audio_bytes = audio.get('bytes') if isinstance(audio, dict) else None
                if audio_bytes and len(audio_bytes) > 1000:
                    st.audio(audio_bytes, format="audio/wav")
                    if st.button("📤 识别并发送 Recognize & Send", key=f"send_voice_{len(st.session_state.messages)}", type="primary", use_container_width=True):
                        with st.spinner("🔄 正在识别 Recognizing..."):
                            recognized_text = speech_to_text_ali(audio_bytes)
                            if recognized_text and recognized_text.strip():
                                st.success(f"🗣️ 识别结果 Result: {recognized_text}")
                                process_input(recognized_text.strip(), role_name, scene, hsk_level)
                            else:
                                st.error("❌ 未能识别，请重试 Recognition failed, please try again")
        except Exception as e:
            st.warning(f"语音组件加载失败 Voice component failed: {e}")

    # 底部按钮
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 重新开始 Restart", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("📚 生词本 Vocab", use_container_width=True):
            st.session_state.page = "vocab"
            st.rerun()
    with col3:
        if st.button("🏠 换角色 Change", use_container_width=True):
            st.session_state.page = "select"
            st.rerun()

def process_input(text, role_name, scene, hsk_level):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": text})

    # 埋点：用户发送消息
    track_event("message_sent", {"role": role_name, "scene": scene, "text_length": len(text)})

    # 构建API消息
    api_messages = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            api_messages.append({"role": "user", "content": msg["content"]})
        else:
            content = msg["content"]
            api_messages.append({"role": "assistant", "content": content.get("chinese", "") if isinstance(content, dict) else str(content)})

    # 调用API获取回复
    response = get_deepseek_response(api_messages, role_name, scene, hsk_level)

    if response:
        st.session_state.messages.append({"role": "assistant", "content": response})
        # 更新用户对话统计
        user_id = st.session_state.get("user_id")
        if user_id:
            update_user_stats(user_id, conversations_delta=1)
    else:
        # API失败时，移除刚添加的用户消息，让用户可以重试
        st.session_state.messages.pop()
        st.warning("⚠️ 发送失败，请重试")

    st.rerun()

def render_ai_message(content, msg_index, role_name):
    if not isinstance(content, dict):
        st.markdown(f"**AI:** {content}")
        return

    chinese = content.get("chinese", "")
    pinyin = content.get("pinyin", "")
    english = content.get("english", "")
    keywords = content.get("keywords", [])

    role_info = ROLES.get(role_name, {})
    gender_icon = "👨" if role_info.get("gender") == "male" else "👩"

    st.markdown(f'<div class="chat-ai"><div class="chinese-text">{chinese}</div><div class="pinyin-text">{pinyin}</div></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button(f"🔊 播放 Play", key=f"play_{msg_index}"):
            with st.spinner("生成语音 Generating..."):
                audio = text_to_speech_ali(chinese, role_name)
                if audio:
                    st.session_state[f"audio_{msg_index}"] = audio
                    st.rerun()
    with col2:
        if st.button("📖 翻译 Translate", key=f"trans_{msg_index}"):
            st.session_state[f"show_trans_{msg_index}"] = not st.session_state.get(f"show_trans_{msg_index}", False)
            st.rerun()

    if f"audio_{msg_index}" in st.session_state and st.session_state[f"audio_{msg_index}"]:
        st.audio(st.session_state[f"audio_{msg_index}"], format="audio/mp3", autoplay=True)

    if st.session_state.get(f"show_trans_{msg_index}", False):
        st.markdown(f'<div class="english-text">📝 {english}</div>', unsafe_allow_html=True)

    if keywords:
        st.markdown("**🏷️ 关键词 Keywords（点击添加 Click to save）：**")
        cols = st.columns(min(len(keywords), 3))
        for idx, kw in enumerate(keywords):
            word = kw.get("word", "") if isinstance(kw, dict) else str(kw)
            meaning = kw.get("meaning", "") if isinstance(kw, dict) else ""
            with cols[idx % 3]:
                if st.button(f"📌 {word}", key=f"kw_{msg_index}_{idx}", help=meaning):
                    if save_word_to_vocab(word, meaning, chinese):
                        st.success(f"✅ '{word}' 已添加 Saved!")

def render_vocab():
    st.markdown("## 📚 我的生词本 My Vocabulary")
    vocab_list = get_all_vocab()

    if not vocab_list:
        st.info("📭 生词本是空的，在对话中点击关键词即可添加！\n\nVocab list is empty. Click keywords in chat to add!")
    else:
        st.markdown(f"共有 **{len(vocab_list)}** 个待学习的生词 words to learn")
        for word_id, word, meaning, context, created_at in vocab_list:
            st.markdown(f'<div class="vocab-card"><div style="font-size:1.4rem;font-weight:600;">{word}</div><div style="color:#666;">{meaning}</div></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 已掌握 Mastered", key=f"master_{word_id}", use_container_width=True):
                    mark_word_mastered(word_id)
                    st.rerun()
            with col2:
                if st.button("🗑️ 删除 Delete", key=f"delete_{word_id}", use_container_width=True):
                    delete_word(word_id)
                    st.rerun()
            st.markdown("---")

    if st.button("⬅️ 返回对话 Back to Chat", use_container_width=True, type="primary"):
        st.session_state.page = "chat" if st.session_state.get("selected_role") else "landing"
        st.rerun()

def render_sidebar():
    with st.sidebar:
        # 用户信息
        if st.session_state.get("logged_in"):
            nickname = st.session_state.get("nickname", "用户")
            st.markdown(f"### 👤 {nickname}")

            # 获取用户统计
            user_id = st.session_state.get("user_id")
            if user_id:
                user_info = get_user_info(user_id)
                if user_info:
                    st.markdown(f"""
                    📊 **学习统计 Stats**
                    - 对话数 Chats: {user_info['total_conversations']}
                    - 生词数 Words: {user_info['total_words_learned']}
                    """)

            st.markdown("---")

        st.markdown("## ⚙️ 设置 Settings")
        if st.session_state.get("selected_role"):
            r = ROLES[st.session_state.selected_role]
            gender = "男声 Male" if r["gender"] == "male" else "女声 Female"
            st.markdown(f"**角色 Role:** {r['avatar']} {st.session_state.selected_role}\n\n**场景 Scene:** {st.session_state.get('selected_scene', '未选择')}\n\n**HSK:** {st.session_state.get('hsk_level', '?')}级\n\n**语音 Voice:** 🔊 {gender}")

        st.markdown("---")
        if st.button("🏠 首页 Home", use_container_width=True, key="sb_home"):
            st.session_state.page = "landing"
            st.rerun()
        if st.button("📚 生词本 Vocab", use_container_width=True, key="sb_vocab"):
            st.session_state.page = "vocab"
            st.rerun()

        # 退出登录按钮
        if st.session_state.get("logged_in"):
            st.markdown("---")
            if st.button("🚪 退出登录 Logout", use_container_width=True, key="sb_logout"):
                # 清除用户状态
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.nickname = None
                st.session_state.page = "landing"
                st.rerun()

        st.markdown("---\n### ℹ️ 关于 About\n**CN Chinese Link** v1.2\n\n🧠 DeepSeek-V3\n🔊 阿里百炼 TTS\n🎤 语音识别 ASR\n💾 用户数据存储")

# ============================================================
# 主函数
# ============================================================
def main():
    st.set_page_config(page_title="中国缘 CN Chinese Link", page_icon="🇨🇳", layout="centered", initial_sidebar_state="collapsed")
    init_database()
    apply_styles()

    if "page" not in st.session_state:
        st.session_state.page = "landing"

    render_sidebar()

    page = st.session_state.page
    if page == "landing":
        render_landing()
    elif page == "select":
        render_selection()
    elif page == "chat":
        render_chat()
    elif page == "vocab":
        render_vocab()
    else:
        st.session_state.page = "landing"
        st.rerun()

if __name__ == "__main__":
    main()
