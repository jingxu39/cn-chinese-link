# 🇨🇳 CN Chinese Link (中国缘)

**遇见你的中国家人和朋友 | Meet Your Chinese Family & Friends**

AI 沉浸式中文学习应用 - 通过角色扮演和真实场景帮助国际中文学习者练习口语

## ✨ 功能特色

### 🎭 六大真实角色
- **王阿姨** (丈母娘 Mother-in-law) - 春节回家、催婚/催生、饭桌礼仪
- **张总** (商业老板 Business Boss) - 项目汇报、商务宴请、薪资谈判
- **小李** (中国朋友 Chinese Friend) - 周末约饭、吐槽工作、聊网络热梗
- **服务员** (餐厅/商店 Waiter/Staff) - 餐厅点餐、商场买衣服、咖啡店点单
- **陈老师** (中文老师 Chinese Teacher) - 作业辅导、考试咨询、留学建议
- **赵姐** (职场同事 Office Colleague) - 点奶茶、八卦聊天、工作协作

### 🎯 智能学习功能
- **HSK 1-6 级难度适配** - 根据学习者水平调整对话难度
- **AI 智能回复** - DeepSeek-V3 提供自然流畅的中文对话
- **语音合成** - 阿里百炼高质量中文语音（男女声适配角色）
- **语音识别** - 支持语音输入
- **生词本** - 点击关键词自动收藏，标记已掌握
- **用户系统** - 邮箱注册登录，数据云端存储
- **数据埋点** - 记录学习行为，生成数据报告

### 📱 移动端友好
- 响应式设计，完美适配手机屏幕
- 中英双语界面
- HTTPS 支持（手机麦克风需要）

## 🚀 快速开始

### 本地运行
```bash
cd cn_chinese_link
pip install -r requirements.txt
streamlit run "手机版本v1.1版本app.py"
```

### 手机访问（HTTPS）
```bash
python start_https_cloudflare.py
```

### 查看数据报告
```bash
python 查看数据报告.py
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 前端框架 | Streamlit |
| LLM | DeepSeek-V3 |
| 语音合成 | 阿里百炼 TTS |
| 语音识别 | 阿里百炼 ASR |
| 数据库 | SQLite |

---

**v1.2** | Powered by DeepSeek & 阿里百炼
