/**
 * 多语言支持 - NHL Commentary Web Client
 * Multi-language Support for NHL Commentary Web Client
 */

class LanguageManager {
    constructor() {
        this.currentLanguage = this.getStoredLanguage() || this.detectBrowserLanguage();
        this.translations = {
            'zh-CN': {
                // 页面标题和头部
                pageTitle: '🏒 NHL LiveStream Commentary',
                connecting: '连接中...',
                connected: '已连接',
                disconnected: '连接断开',
                connectionError: '连接错误',
                
                // 控制面板
                controlPanel: '控制面板',
                selectGame: '选择比赛:',
                pleaseSelectGame: '请选择比赛...',
                voiceStyle: '解说风格:',
                enthusiastic: '兴奋解说',
                dramatic: '戏剧解说',
                calm: '平静解说',
                startCommentary: '开始解说',
                stopCommentary: '停止解说',
                pauseCommentary: '暂停',
                resumeCommentary: '继续',
                
                // 解说区域
                liveCommentary: '实时解说',
                waitingToStart: '等待开始...',
                commentating: '正在解说...',
                paused: '已暂停',
                stopped: '已停止',
                commentaryHistory: '解说历史',
                noCommentaryHistory: '暂无解说历史',
                selectGameToStart: '选择比赛并点击"开始解说"来开始实时解说',
                
                // 音频区域
                audioPlayback: '音频播放',
                noAudio: '无音频',
                audioQueue: '音频队列',
                noAudioFiles: '暂无音频文件',
                loading: '加载中...',
                readyToPlay: '准备播放',
                playing: '播放中',
                audioError: '播放错误',
                muted: '已静音',
                unmuted: '已取消静音',
                volume: '音量',
                
                // 比赛数据
                gameData: '比赛数据',
                score: '比分',
                homeTeam: '主队',
                awayTeam: '客队',
                vs: 'VS',
                gameStatus: '比赛状态',
                period1: '第1节',
                period2: '第2节',
                period3: '第3节',
                overtime: '加时赛',
                shootout: '点球大战',
                final: '终场',
                recentEvents: '最新事件',
                noEvents: '暂无比赛事件',
                systemStatus: '系统状态',
                dataAgent: '数据代理',
                commentaryAgent: '解说代理',
                audioAgent: '音频代理',
                online: '在线',
                offline: '离线',
                
                // 通知和消息
                playingAudio: '正在播放解说音频...',
                commentaryCompleted: '解说已完成',
                pleaseSelectGameFirst: '请先选择一场比赛',
                startingCommentary: '正在启动解说...',
                stoppingCommentary: '正在停止解说...',
                
                // 游戏信息
                games: {
                    '2024030412': 'TOR vs BOS - 季后赛',
                    '2024020123': 'NYR vs PHI - 常规赛',
                    '2024020456': 'EDM vs CGY - 常规赛'
                },
                
                // 队伍名称
                teams: {
                    'Toronto Maple Leafs': '多伦多枫叶队',
                    'Boston Bruins': '波士顿棕熊队',
                    'New York Rangers': '纽约游骑兵队',
                    'Philadelphia Flyers': '费城飞人队',
                    'Edmonton Oilers': '埃德蒙顿油人队',
                    'Calgary Flames': '卡尔加里火焰队'
                },
                
                // 页脚
                footer: '版权所有 © 2024 NHL LiveStream Commentary | 由 Google ADK & Gemini AI 驱动'
            },
            
            'en-US': {
                // Page title and header
                pageTitle: '🏒 NHL LiveStream Commentary',
                connecting: 'Connecting...',
                connected: 'Connected',
                disconnected: 'Disconnected',
                connectionError: 'Connection Error',
                
                // Control panel
                controlPanel: 'Control Panel',
                selectGame: 'Select Game:',
                pleaseSelectGame: 'Please select a game...',
                voiceStyle: 'Voice Style:',
                enthusiastic: 'Enthusiastic',
                dramatic: 'Dramatic',
                calm: 'Calm',
                startCommentary: 'Start Commentary',
                stopCommentary: 'Stop Commentary',
                pauseCommentary: 'Pause',
                resumeCommentary: 'Resume',
                
                // Commentary area
                liveCommentary: 'Live Commentary',
                waitingToStart: 'Waiting to start...',
                commentating: 'Commentating...',
                paused: 'Paused',
                stopped: 'Stopped',
                commentaryHistory: 'Commentary History',
                noCommentaryHistory: 'No commentary history',
                selectGameToStart: 'Select a game and click "Start Commentary" to begin live commentary',
                
                // Audio area
                audioPlayback: 'Audio Playback',
                noAudio: 'No Audio',
                audioQueue: 'Audio Queue',
                noAudioFiles: 'No audio files',
                loading: 'Loading...',
                readyToPlay: 'Ready to play',
                playing: 'Playing',
                audioError: 'Playback error',
                muted: 'Muted',
                unmuted: 'Unmuted',
                volume: 'Volume',
                
                // Game data
                gameData: 'Game Data',
                score: 'Score',
                homeTeam: 'Home',
                awayTeam: 'Away',
                vs: 'VS',
                gameStatus: 'Game Status',
                period1: '1st Period',
                period2: '2nd Period', 
                period3: '3rd Period',
                overtime: 'Overtime',
                shootout: 'Shootout',
                final: 'Final',
                recentEvents: 'Recent Events',
                noEvents: 'No game events',
                systemStatus: 'System Status',
                dataAgent: 'Data Agent',
                commentaryAgent: 'Commentary Agent',
                audioAgent: 'Audio Agent',
                online: 'Online',
                offline: 'Offline',
                
                // Notifications and messages
                playingAudio: 'Playing commentary audio...',
                commentaryCompleted: 'Commentary completed',
                pleaseSelectGameFirst: 'Please select a game first',
                startingCommentary: 'Starting commentary...',
                stoppingCommentary: 'Stopping commentary...',
                
                // Game information
                games: {
                    '2024030412': 'TOR vs BOS - Playoffs',
                    '2024020123': 'NYR vs PHI - Regular Season',
                    '2024020456': 'EDM vs CGY - Regular Season'
                },
                
                // Team names
                teams: {
                    'Toronto Maple Leafs': 'Toronto Maple Leafs',
                    'Boston Bruins': 'Boston Bruins',
                    'New York Rangers': 'New York Rangers',
                    'Philadelphia Flyers': 'Philadelphia Flyers',
                    'Edmonton Oilers': 'Edmonton Oilers',
                    'Calgary Flames': 'Calgary Flames'
                },
                
                // Footer
                footer: '© 2024 NHL LiveStream Commentary | Powered by Google ADK & Gemini AI'
            }
        };
    }
    
    /**
     * 检测浏览器语言
     */
    detectBrowserLanguage() {
        const browserLang = navigator.language || navigator.userLanguage;
        if (browserLang.startsWith('zh')) {
            return 'zh-CN';
        }
        return 'en-US';
    }
    
    /**
     * 获取存储的语言设置
     */
    getStoredLanguage() {
        return localStorage.getItem('nhl-commentary-language');
    }
    
    /**
     * 存储语言设置
     */
    setStoredLanguage(language) {
        localStorage.setItem('nhl-commentary-language', language);
    }
    
    /**
     * 切换语言
     */
    switchLanguage(language) {
        if (this.translations[language]) {
            this.currentLanguage = language;
            this.setStoredLanguage(language);
            this.updatePageContent();
            
            // 触发语言切换事件
            window.dispatchEvent(new CustomEvent('languageChanged', {
                detail: { language: language }
            }));
        }
    }
    
    /**
     * 获取翻译文本
     */
    t(key) {
        const keys = key.split('.');
        let result = this.translations[this.currentLanguage];
        
        for (const k of keys) {
            if (result && result[k] !== undefined) {
                result = result[k];
            } else {
                // 如果当前语言没有该键，尝试使用英文
                result = this.translations['en-US'];
                for (const k2 of keys) {
                    if (result && result[k2] !== undefined) {
                        result = result[k2];
                    } else {
                        return key; // 如果都没有，返回键名
                    }
                }
                break;
            }
        }
        
        return result || key;
    }
    
    /**
     * 更新页面内容
     */
    updatePageContent() {
        // 更新页面标题
        document.title = this.t('pageTitle');
        
        // 更新所有带有 data-i18n 属性的元素
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);
            
            if (element.tagName === 'INPUT' && element.type === 'text') {
                element.placeholder = translation;
            } else if (element.tagName === 'OPTION') {
                element.textContent = translation;
            } else {
                // 保留HTML标签，只替换文本内容
                const htmlContent = element.innerHTML;
                const iconMatch = htmlContent.match(/^(<i[^>]*><\/i>\s*)/);
                if (iconMatch) {
                    element.innerHTML = iconMatch[1] + translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
        
        // 更新语言选择器的显示
        this.updateLanguageSelector();
    }
    
    /**
     * 更新语言选择器
     */
    updateLanguageSelector() {
        const languageSelect = document.getElementById('languageSelect');
        if (languageSelect) {
            languageSelect.value = this.currentLanguage;
        }
    }
    
    /**
     * 获取当前语言
     */
    getCurrentLanguage() {
        return this.currentLanguage;
    }
    
    /**
     * 获取支持的语言列表
     */
    getSupportedLanguages() {
        return Object.keys(this.translations);
    }
    
    /**
     * 格式化时间（根据语言环境）
     */
    formatTime(date) {
        if (this.currentLanguage === 'zh-CN') {
            return date.toLocaleString('zh-CN');
        } else {
            return date.toLocaleString('en-US');
        }
    }
}

// 导出语言管理器
window.LanguageManager = LanguageManager; 