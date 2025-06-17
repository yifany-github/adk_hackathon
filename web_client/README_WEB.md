# 🏒 NHL Commentary Web Client

现代化的NHL实时解说Web界面，基于您的多智能体解说系统构建。

## ✨ 主要特性

- 🎮 **直观控制** - 简单易用的解说控制面板
- 🎙️ **实时解说** - 实时显示解说文本和历史记录
- 🔊 **音频播放** - 支持多种语音风格和音频队列管理
- 📊 **比赛数据** - 实时比分、时间和事件显示
- 📱 **响应式设计** - 支持桌面和移动设备
- ⚡ **WebSocket实时通信** - 低延迟的实时数据更新
- 🎨 **现代UI** - 冰球主题的美观界面设计

## 🚀 快速开始

### 1. 启动Web服务器

```bash
# 进入web_client目录
cd web_client

# 启动服务器（会自动安装依赖）
python start_server.py
```

### 2. 打开浏览器

访问 http://localhost:8080 开始使用

## 🎮 使用指南

### 控制面板
- **选择比赛**: 从下拉菜单选择要解说的比赛
- **解说风格**: 
  - 兴奋解说 (enthusiastic) - 适合进球等激动时刻
  - 戏剧解说 (dramatic) - 适合关键时刻
  - 平静解说 (calm) - 适合常规解说
- **控制按钮**:
  - 🎬 开始解说 - 启动实时解说
  - ⏹️ 停止解说 - 完全停止解说
  - ⏸️ 暂停 - 暂停/恢复解说

### 实时解说区域
- **当前解说**: 显示最新的解说内容
- **解说历史**: 显示最近20条解说记录，包含时间戳

### 音频控制
- **音频播放器**: HTML5音频播放器，支持播放控制
- **音量控制**: 滑块调节音量
- **静音按钮**: 快速静音/取消静音
- **音频队列**: 显示待播放的音频列表

### 比赛数据面板
- **比分显示**: 实时比分和队伍信息
- **比赛状态**: 当前节次和比赛时间
- **最新事件**: 最近发生的比赛事件
- **系统状态**: 三个AI代理的在线状态

## ⌨️ 键盘快捷键

- `Ctrl + Space`: 开始/暂停解说
- `Ctrl + S`: 停止解说
- `Ctrl + M`: 静音/取消静音

## 🔗 技术架构

### 前端技术栈
- **HTML5** - 语义化标记
- **CSS3** - 现代样式和动画
- **Vanilla JavaScript** - 原生JS，无框架依赖
- **WebSocket** - 实时双向通信
- **Font Awesome** - 图标库
- **Google Fonts** - Inter字体

### 后端技术栈
- **Flask** - Web框架
- **Flask-SocketIO** - WebSocket支持
- **Eventlet** - 异步处理

### 数据流
```
Browser ←→ WebSocket ←→ Flask Server ←→ NHL Pipeline
   ↓           ↓            ↓             ↓
UI控制     实时通信      会话管理       AI解说生成
```

## 📁 文件结构

```
web_client/
├── index.html          # 主HTML文件
├── styles.css          # CSS样式文件
├── script.js          # JavaScript逻辑
├── start_server.py    # 简化启动脚本
├── server.py          # 完整服务器实现
├── requirements_web.txt # Web依赖
└── README_WEB.md      # 使用说明
```

## 🎨 UI特性

### 设计主题
- **冰球蓝色调**: 主色调使用冰球场的蓝色系
- **渐变背景**: 深色渐变背景，营造专业氛围
- **毛玻璃效果**: 卡片使用backdrop-filter创建现代感
- **动画效果**: 平滑的过渡和悬停效果

### 响应式设计
- **桌面**: 网格布局，多列显示
- **平板**: 自适应布局调整
- **手机**: 单列布局，触控优化

### 状态指示
- **连接状态**: 实时显示WebSocket连接状态
- **解说状态**: 清晰的解说进行状态
- **代理状态**: 三个AI代理的运行状态
- **音频状态**: 当前音频播放状态

## 🔧 自定义配置

### 修改服务器端口
```python
# 在start_server.py中修改
server = SimpleNHLWebServer(host='localhost', port=8888)
```

### 自定义解说内容
在`start_server.py`的`run_demo_commentary`方法中修改`commentaries`数组

### 集成真实API
替换`server.py`中的模拟数据为真实的NHL API调用

## 🐛 故障排除

### 端口被占用
```bash
# 查看端口占用
lsof -i :8080

# 或使用不同端口
python start_server.py --port 8888
```

### 依赖安装失败
```bash
# 手动安装依赖
pip install Flask Flask-SocketIO eventlet
```

### WebSocket连接失败
- 检查防火墙设置
- 确认端口未被占用
- 尝试使用不同浏览器

## 🚀 生产环境部署

### 使用Gunicorn
```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8080 server:app
```

### Docker部署
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements_web.txt
CMD ["python", "start_server.py", "--host", "0.0.0.0"]
```

## 📝 许可证

与主项目使用相同的许可证。

---

**Powered by Google ADK & Gemini AI** 🚀 