# 🌍 Multi-Language Support / 多语言支持

NHL Commentary Web Client 现在支持中英文双语界面和解说！

## ✨ 功能特性 / Features

### 🇨🇳 中文支持
- **界面语言**: 完整的中文界面翻译
- **解说内容**: 中文冰球解说
- **语音风格**: 支持兴奋、戏剧、平静三种风格
- **自动检测**: 浏览器语言自动检测

### 🇺🇸 English Support
- **Interface Language**: Complete English interface translation
- **Commentary Content**: English hockey commentary
- **Voice Styles**: Support for enthusiastic, dramatic, and calm styles
- **Auto Detection**: Automatic browser language detection

## 🚀 使用方法 / How to Use

### 1. 语言切换 / Language Switching
在页面右上角选择语言：
- 🇨🇳 **中文** - 中文界面和解说
- 🇺🇸 **English** - English interface and commentary

### 2. 自动检测 / Auto Detection
- 首次访问时自动检测浏览器语言
- 支持语言偏好记忆
- 设置会保存在本地存储中

### 3. 解说内容 / Commentary Content

#### 中文解说示例 / Chinese Commentary Examples
```
🏒 比赛开始！多伦多枫叶队主场迎战波士顿棕熊队！
⚡ McDavid带球快速突破，速度惊人！
🎯 Matthews起脚射门！
⚽ 进球！！！多伦多枫叶队得分！
```

#### English Commentary Examples
```
🏒 Game on! Toronto Maple Leafs hosting the Boston Bruins at home!
⚡ McDavid with a lightning-fast breakaway, incredible speed!
🎯 Matthews takes the shot!
⚽ GOAL!!! Toronto Maple Leafs light the lamp!
```

## 🔧 技术实现 / Technical Implementation

### 文件结构 / File Structure
```
web_client/
├── lang.js              # 多语言管理器
├── index.html          # 添加了 data-i18n 属性
├── script.js           # 集成多语言支持
├── styles.css          # 多语言字体优化
└── start_server.py     # 后端多语言解说
```

### 核心组件 / Core Components

#### 1. LanguageManager 类
- 管理语言切换
- 处理翻译文本
- 自动检测浏览器语言
- 本地存储语言偏好

#### 2. 国际化标记 / i18n Markup
HTML元素使用 `data-i18n` 属性：
```html
<h2 data-i18n="controlPanel">控制面板</h2>
<button data-i18n="startCommentary">开始解说</button>
```

#### 3. 动态翻译 / Dynamic Translation
JavaScript中使用 `t()` 方法：
```javascript
this.updateAudioStatus(this.t('noAudio'));
alert(this.t('pleaseSelectGameFirst'));
```

## 🎨 界面适配 / UI Adaptation

### 字体优化 / Font Optimization
- **中文**: PingFang SC, Hiragino Sans GB, Microsoft YaHei
- **English**: Inter, system fonts
- **响应式**: 自动适配不同语言的文本长度

### 布局调整 / Layout Adjustments
- 按钮文本自动适配
- 下拉菜单翻译
- 状态指示器多语言
- 通知消息本地化

## 🔄 实时切换 / Real-time Switching

### 即时生效 / Immediate Effect
- 无需刷新页面
- 保持当前状态
- 音频播放不中断
- 设置自动保存

### 服务器通信 / Server Communication
- 自动发送语言偏好到服务器
- 解说内容根据语言生成
- WebSocket消息包含语言信息

## 📱 响应式支持 / Responsive Support

### 移动设备 / Mobile Devices
- 语言选择器适配触屏
- 文本大小自动调整
- 按钮间距优化

### 不同屏幕 / Different Screens
- 桌面：完整语言选择器
- 平板：紧凑布局
- 手机：下拉菜单

## 🛠️ 开发者指南 / Developer Guide

### 添加新语言 / Adding New Languages

1. **更新 lang.js**:
```javascript
'fr-FR': {
    pageTitle: '🏒 Commentaire NHL en Direct',
    startCommentary: 'Commencer Commentaire',
    // ... 更多翻译
}
```

2. **更新服务器解说**:
```python
elif language == 'fr-FR':
    commentaries = [
        "🏒 Le jeu commence! Toronto contre Boston!",
        # ... 更多解说
    ]
```

3. **添加语言选项**:
```html
<option value="fr-FR">Français</option>
```

### 本地化最佳实践 / Localization Best Practices

- **键名规范**: 使用点分隔的键名 (`section.item`)
- **文本长度**: 考虑不同语言的文本长度差异
- **文化适配**: 注意文化差异和本地化表达
- **回退机制**: 提供英文作为默认回退语言

## 🐛 故障排除 / Troubleshooting

### 常见问题 / Common Issues

**Q: 语言切换不生效？**
A: 检查浏览器控制台是否有JavaScript错误

**Q: 解说还是原来的语言？**
A: 重新开始解说，新语言设置会在下次开始时生效

**Q: 某些文本没有翻译？**
A: 检查元素是否有 `data-i18n` 属性

### 调试模式 / Debug Mode
```javascript
// 在浏览器控制台中检查当前语言
console.log(window.nhlClient.languageManager.getCurrentLanguage());

// 手动触发页面更新
window.nhlClient.languageManager.updatePageContent();
```

## 🎯 未来计划 / Future Plans

- 🇪🇸 西班牙语支持
- 🇫🇷 法语支持
- 🇩🇪 德语支持
- 🎙️ 多语言语音合成
- 📊 语言使用统计

---

**Enjoy the NHL Commentary experience in your preferred language! / 用您喜欢的语言享受NHL解说体验！** 🏒✨ 