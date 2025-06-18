/**
 * NHL LiveStream Commentary Web Client
 * JavaScript逻辑控制器
 */

class NHLCommentaryClient {
    constructor() {
        this.websocket = null;
        this.currentGameId = null;
        this.isRunning = false;
        this.isPaused = false;
        this.audioQueue = [];
        this.currentAudioIndex = 0;
        this.commentaryHistory = [];
        this.languageManager = new LanguageManager();
        
        // DOM元素引用
        this.elements = {
            // 控制元素
            gameInput: document.getElementById('gameInput'),
            voiceStyle: document.getElementById('voiceStyle'),
            startBtn: document.getElementById('startBtn'),
            stopBtn: document.getElementById('stopBtn'),
            pauseBtn: document.getElementById('pauseBtn'),
            languageSelect: document.getElementById('languageSelect'),
            
            // 状态显示
            connectionStatus: document.getElementById('connectionStatus'),
            commentaryStatus: document.getElementById('commentaryStatus'),
            
            // 解说区域
            currentCommentary: document.getElementById('currentCommentary'),
            commentaryHistory: document.getElementById('commentaryHistory'),
            
            // 音频控制
            audioPlayer: document.getElementById('audioPlayer'),
            muteBtn: document.getElementById('muteBtn'),
            volumeSlider: document.getElementById('volumeSlider'),
            audioStatus: document.getElementById('audioStatus'),
            audioQueue: document.getElementById('audioQueue'),
            audioNotification: document.getElementById('audioNotification'),
            
            // 比赛数据
            scoreDisplay: document.getElementById('scoreDisplay'),
            gameStatus: document.getElementById('gameStatus'),
            recentEvents: document.getElementById('recentEvents'),
            dataAgentStatus: document.getElementById('dataAgentStatus')
        };
        
        this.init();
    }
    
    init() {
        this.initializeEventListeners();
        this.initializeAudioPlayer();
        this.initializeLanguage();
        this.initializeStatus();
        this.connectWebSocket();
    }
    
    initializeEventListeners() {
        // 控制按钮事件
        this.elements.startBtn.addEventListener('click', () => this.startCommentary());
        this.elements.stopBtn.addEventListener('click', () => this.stopCommentary());
        this.elements.pauseBtn.addEventListener('click', () => this.pauseCommentary());
        
        // 音频控制事件
        this.elements.muteBtn.addEventListener('click', () => this.toggleMute());
        this.elements.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        
        // 语言切换事件
        this.elements.languageSelect.addEventListener('change', (e) => {
            this.changeLanguage(e.target.value);
        });
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // 音频播放器事件
        this.elements.audioPlayer.addEventListener('ended', () => this.playNextAudio());
        this.elements.audioPlayer.addEventListener('error', () => {
            console.error('音频播放错误');
            this.playNextAudio();
        });
    }
    
    handleKeyboardShortcuts(event) {
        // Ctrl + Space: 开始/暂停
        if (event.ctrlKey && event.code === 'Space') {
            event.preventDefault();
            if (!this.isRunning) {
                this.startCommentary();
            } else if (this.isPaused) {
                this.pauseCommentary(); // Resume
            } else {
                this.pauseCommentary(); // Pause
            }
        }
        
        // Ctrl + S: 停止
        if (event.ctrlKey && event.key === 's') {
            event.preventDefault();
            this.stopCommentary();
        }
        
        // Ctrl + M: 静音
        if (event.ctrlKey && event.key === 'm') {
            event.preventDefault();
            this.toggleMute();
        }
    }
    
    initializeAudioPlayer() {
        // 设置默认音量
        this.elements.audioPlayer.volume = 0.7;
        this.elements.volumeSlider.value = 70;
    }
    
    initializeLanguage() {
        // 设置语言选择器的值
        this.elements.languageSelect.value = this.languageManager.getCurrentLanguage();
        
        // 应用初始语言
        this.updateDynamicContent();
        
        // 监听语言变化
        this.languageManager.onChange = () => {
            this.updateDynamicContent();
        };
    }
    
    changeLanguage(language) {
        this.languageManager.setLanguage(language);
    }
    
    t(key) {
        return this.languageManager.t(key);
    }
    
    initializeStatus() {
        // 初始化连接状态
        this.updateConnectionStatus(this.t('connecting'), 'connecting');
        
        // 初始化Agent状态
        this.updateAgentStatus('dataAgentStatus', 'offline');
        this.updateAgentStatus('commentaryAgentStatus', 'offline');
        this.updateAgentStatus('audioAgentStatus', 'offline');
    }
    
    updateDynamicContent() {
        // 更新所有带有 data-i18n 属性的元素
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.languageManager.t(key);
            if (translation) {
                if (element.tagName === 'INPUT' && element.type === 'text') {
                    element.placeholder = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
        
        // 更新解说历史
        this.updateCommentaryHistory();
    }
    
    /**
     * 连接WebSocket
     */
    connectWebSocket() {
        try {
            // 使用Socket.IO客户端
            if (typeof io !== 'undefined') {
                this.websocket = io();
                this.setupSocketIOEvents();
            } else {
                // 如果Socket.IO不可用，显示错误
                console.error('Socket.IO不可用，无法连接到服务器');
                this.updateConnectionStatus('连接失败', 'error');
            }
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateConnectionStatus(this.t('connectionError'), 'error');
        }
    }
    
    /**
     * 设置Socket.IO事件
     */
    setupSocketIOEvents() {
        this.websocket.on('connect', () => {
            console.log('Socket.IO连接已建立');
            this.updateConnectionStatus(this.t('connected'), 'connected');
            this.updateAgentStatus('dataAgentStatus', 'online');
        });
        
        this.websocket.on('disconnect', () => {
            console.log('Socket.IO连接已断开');
            this.updateConnectionStatus(this.t('disconnected'), 'disconnected');
            this.updateAgentStatus('dataAgentStatus', 'offline');
            this.updateAgentStatus('commentaryAgentStatus', 'offline');
            this.updateAgentStatus('audioAgentStatus', 'offline');
        });
        
        this.websocket.on('commentary', (data) => {
            this.handleCommentaryUpdate(data.data);
        });
        
        this.websocket.on('audio', (data) => {
            this.handleAudioUpdate(data.data);
        });
        
        this.websocket.on('gameData', (data) => {
            this.handleGameDataUpdate(data.data);
        });
        
        this.websocket.on('status', (data) => {
            console.log('收到状态更新:', data);
        });
        
        this.websocket.on('error', (data) => {
            this.handleError(data.data);
        });
    }
    
    /**
     * 发送WebSocket消息
     */
    sendMessage(type, data) {
        if (this.websocket && this.websocket.connected) {
            this.websocket.emit(type, data);
        }
    }
    
    /**
     * 开始解说
     */
    startCommentary() {
        const gameId = this.elements.gameInput.value.trim();
        if (!gameId) {
            alert('请输入比赛ID');
            return;
        }
        
        this.currentGameId = gameId;
        this.isRunning = true;
        this.isPaused = false;
        
        // 更新UI状态
        this.elements.startBtn.disabled = true;
        this.elements.stopBtn.disabled = false;
        this.elements.pauseBtn.disabled = false;
        this.elements.commentaryStatus.textContent = this.t('commentating');
        
        // 发送开始命令到后端
        if (this.websocket && this.websocket.connected) {
            this.sendMessage('start', {
                gameId: gameId,
                voiceStyle: this.elements.voiceStyle.value,
                language: this.languageManager.getCurrentLanguage()
            });
        } else {
            alert('服务器连接断开，请刷新页面重试');
        }
        
        console.log(`开始解说比赛: ${gameId}`);
    }
    
    /**
     * 停止解说
     */
    stopCommentary() {
        this.isRunning = false;
        this.isPaused = false;
        
        // 更新UI状态
        this.elements.startBtn.disabled = false;
        this.elements.stopBtn.disabled = true;
        this.elements.pauseBtn.disabled = true;
        this.elements.commentaryStatus.textContent = this.t('stopped');
        
        // 发送停止命令到后端
        if (this.websocket && this.websocket.connected) {
            this.sendMessage('stop', {});
        }
        
        // 清空音频队列
        this.clearAudioQueue();
        
        console.log('停止解说');
    }
    
    /**
     * 暂停/继续解说
     */
    pauseCommentary() {
        if (!this.isRunning) return;
        
        this.isPaused = !this.isPaused;
        
        // 更新UI状态
        if (this.isPaused) {
            this.elements.commentaryStatus.textContent = this.t('paused');
            this.elements.pauseBtn.innerHTML = '<i class="fas fa-play"></i> ' + this.t('resumeCommentary');
            
            // 发送暂停命令
            if (this.websocket && this.websocket.connected) {
                this.sendMessage('pause', {});
            }
        } else {
            this.elements.commentaryStatus.textContent = this.t('commentating');
            this.elements.pauseBtn.innerHTML = '<i class="fas fa-pause"></i> ' + this.t('pauseCommentary');
            
            // 发送继续命令
            if (this.websocket && this.websocket.connected) {
                this.sendMessage('resume', {});
            }
        }
        
        console.log(this.isPaused ? '暂停解说' : '继续解说');
    }
    
    /**
     * 处理解说更新
     */
    handleCommentaryUpdate(data) {
        this.addCommentary(data.text);
        this.updateAgentStatus('commentaryAgentStatus', 'online');
    }
    
    /**
     * 处理音频更新
     */
    handleAudioUpdate(data) {
        this.addToAudioQueue(data);
        this.updateAgentStatus('audioAgentStatus', 'online');
    }
    
    /**
     * 处理比赛数据更新
     */
    handleGameDataUpdate(data) {
        this.updateGameData(data);
        this.updateAgentStatus('dataAgentStatus', 'online');
    }
    
    /**
     * 处理Agent状态更新
     */
    handleAgentStatusUpdate(data) {
        Object.keys(data).forEach(agent => {
            const elementId = agent + 'Status';
            this.updateAgentStatus(elementId, data[agent]);
        });
    }
    
    /**
     * 处理错误
     */
    handleError(error) {
        console.error('收到错误:', error);
        alert('发生错误: ' + (error.message || '未知错误'));
    }
    
    /**
     * 添加解说文本
     */
    addCommentary(text) {
        // 更新当前解说显示
        this.elements.currentCommentary.innerHTML = `
            <div class="commentary-text">${text}</div>
        `;
        
        // 添加到历史记录
        this.commentaryHistory.unshift({
            text: text,
            timestamp: new Date(),
            id: Date.now()
        });
        
        // 限制历史记录数量
        if (this.commentaryHistory.length > 20) {
            this.commentaryHistory = this.commentaryHistory.slice(0, 20);
        }
        
        // 更新历史显示
        this.updateCommentaryHistory();
    }
    
    /**
     * 更新解说历史显示
     */
    updateCommentaryHistory() {
        const historyContainer = this.elements.commentaryHistory.querySelector('.history-list') || 
                                this.elements.commentaryHistory;
        
        if (this.commentaryHistory.length === 0) {
            historyContainer.innerHTML = `<div class="history-placeholder">${this.t('noCommentaryHistory')}</div>`;
            return;
        }
        
        const historyHTML = this.commentaryHistory.map(item => `
            <div class="history-item">
                <div class="timestamp">${item.timestamp.toLocaleTimeString()}</div>
                <div class="text">${item.text}</div>
            </div>
        `).join('');
        
        historyContainer.innerHTML = historyHTML;
    }
    
    /**
     * 添加到音频队列
     */
    addToAudioQueue(audioData) {
        this.audioQueue.push(audioData);
        this.updateAudioQueueDisplay();
        
        // 如果当前没有播放音频，开始播放
        if (!this.elements.audioPlayer.src || this.elements.audioPlayer.ended) {
            this.playNextAudio();
        }
    }
    
    /**
     * 播放下一个音频
     */
    playNextAudio() {
        if (this.audioQueue.length === 0) {
            this.updateAudioStatus(this.t('noAudio'));
            return;
        }
        
        const audioData = this.audioQueue.shift();
        this.currentAudioIndex++;
        
        // 设置音频源
        if (audioData.url && audioData.url.startsWith('/api/audio/')) {
            // 使用服务器音频文件
            this.elements.audioPlayer.src = audioData.url;
            this.updateAudioStatus(this.t('loading'));
            
            // 尝试播放
            this.elements.audioPlayer.play()
                .then(() => {
                    this.updateAudioStatus(this.t('playing'));
                    this.showAudioNotification(this.t('playingAudio'));
                })
                .catch(error => {
                    console.error('音频播放失败:', error);
                    this.updateAudioStatus(this.t('audioError'));
                    // 继续播放下一个
                    setTimeout(() => this.playNextAudio(), 1000);
                });
        } else {
            // 跳过无效的音频
            console.warn('跳过无效音频:', audioData);
            this.playNextAudio();
        }
        
        this.updateAudioQueueDisplay();
    }
    
    /**
     * 更新音频队列显示
     */
    updateAudioQueueDisplay() {
        if (this.audioQueue.length === 0) {
            this.elements.audioQueue.innerHTML = `
                <div class="queue-placeholder">${this.t('noAudioFiles')}</div>
            `;
            return;
        }
        
        const queueHTML = this.audioQueue.map((audio, index) => `
            <div class="queue-item ${index === 0 ? 'next' : ''}">
                <div class="queue-text">${audio.text.substring(0, 50)}${audio.text.length > 50 ? '...' : ''}</div>
                <div class="queue-style">${audio.style}</div>
            </div>
        `).join('');
        
        this.elements.audioQueue.innerHTML = queueHTML;
    }
    
    /**
     * 清空音频队列
     */
    clearAudioQueue() {
        this.audioQueue = [];
        this.elements.audioPlayer.pause();
        this.elements.audioPlayer.src = '';
        this.updateAudioQueueDisplay();
        this.updateAudioStatus(this.t('noAudio'));
    }
    
    /**
     * 切换静音
     */
    toggleMute() {
        if (this.elements.audioPlayer.muted) {
            this.elements.audioPlayer.muted = false;
            this.elements.muteBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
            this.showAudioNotification(this.t('unmuted'));
        } else {
            this.elements.audioPlayer.muted = true;
            this.elements.muteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
            this.showAudioNotification(this.t('muted'));
        }
    }
    
    /**
     * 设置音量
     */
    setVolume(value) {
        const volume = value / 100;
        this.elements.audioPlayer.volume = volume;
        console.log(`音量设置为: ${value}%`);
    }
    
    /**
     * 更新音频状态
     */
    updateAudioStatus(status) {
        this.elements.audioStatus.textContent = status;
    }
    
    /**
     * 显示音频通知
     */
    showAudioNotification(message) {
        this.elements.audioNotification.querySelector('span').textContent = message;
        this.elements.audioNotification.classList.add('show');
        
        // 3秒后隐藏通知
        setTimeout(() => {
            this.elements.audioNotification.classList.remove('show');
        }, 3000);
    }
    
    /**
     * 更新比赛数据
     */
    updateGameData(data) {
        // 更新比分
        if (data.homeTeam && data.awayTeam) {
            this.elements.scoreDisplay.innerHTML = `
                <div class="team">
                    <span class="team-name">${data.homeTeam.name || data.homeTeam.abbreviation}</span>
                    <span class="team-score">${data.homeTeam.score}</span>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <span class="team-name">${data.awayTeam.name || data.awayTeam.abbreviation}</span>
                    <span class="team-score">${data.awayTeam.score}</span>
                </div>
            `;
        }
        
        // 更新比赛状态
        if (data.period && data.time) {
            let statusHtml = `
                <div class="period">${data.period}</div>
                <div class="time">${data.time}</div>
            `;
            
            // 添加比赛强度指示器
            if (data.intensity) {
                const intensityText = data.intensity === 'high' ? '高强度' : 
                                    data.intensity === 'medium' ? '中强度' : '低强度';
                const intensityClass = `intensity-${data.intensity}`;
                statusHtml += `<div class="intensity ${intensityClass}">${intensityText}</div>`;
            }
            
            // 添加比赛情况
            if (data.gameContext && data.gameContext.situation) {
                statusHtml += `<div class="situation">${data.gameContext.situation}</div>`;
            }
            
            this.elements.gameStatus.innerHTML = statusHtml;
        }
        
        // 更新最新事件 - 显示多个事件
        if (data.events && data.events.length > 0) {
            const eventsHtml = data.events.map(event => `
                <div class="event-item">
                    <div class="event-time">${event.time || new Date().toLocaleTimeString()}</div>
                    <div class="event-description">${event.summary}</div>
                    <div class="event-type ${event.event_type}">${event.event_type}</div>
                </div>
            `).join('');
            
            this.elements.recentEvents.innerHTML = eventsHtml;
        } else if (data.lastEvent) {
            // 后备方案：显示单个最新事件
            this.elements.recentEvents.innerHTML = `
                <div class="event-item">
                    <div class="event-time">${new Date().toLocaleTimeString()}</div>
                    <div class="event-description">${data.lastEvent}</div>
                </div>
            `;
        }
        
        // 显示关键要点（如果页面上有相应元素）
        this.updateKeyPoints(data.keyPoints);
        
        // 更新比赛上下文信息
        this.updateGameContext(data.gameContext);
    }
    
    /**
     * 更新关键要点
     */
    updateKeyPoints(keyPoints) {
        const keyPointsElement = document.getElementById('keyPoints');
        if (!keyPointsElement || !keyPoints || keyPoints.length === 0) {
            return;
        }
        
        const pointsHtml = keyPoints.slice(0, 3).map(point => `
            <div class="key-point">${point}</div>
        `).join('');
        
        keyPointsElement.innerHTML = pointsHtml;
    }
    
    /**
     * 更新比赛上下文
     */
    updateGameContext(gameContext) {
        if (!gameContext) return;
        
        const contextElement = document.getElementById('gameContext');
        if (!contextElement) return;
        
        let contextHtml = '';
        
        if (gameContext.momentum_shift) {
            contextHtml += `<div class="momentum">动量转换: ${gameContext.momentum_shift}</div>`;
        }
        
        if (gameContext.key_players && gameContext.key_players.length > 0) {
            const playersText = gameContext.key_players.slice(0, 3).join(', ');
            contextHtml += `<div class="key-players">关键球员: ${playersText}</div>`;
        }
        
        if (gameContext.tactical_notes) {
            contextHtml += `<div class="tactical-notes">${gameContext.tactical_notes}</div>`;
        }
        
        contextElement.innerHTML = contextHtml;
    }
    
    /**
     * 获取推荐文本
     */
    getRecommendationText(recommendation) {
        const recommendationMap = {
            'emphasize_momentum': '强调比赛动量变化',
            'highlight_skills': '突出球员技巧表现',
            'build_tension': '营造紧张气氛',
            'celebrate_goals': '庆祝进球时刻',
            'analyze_strategy': '分析战术策略'
        };
        
        return recommendationMap[recommendation] || recommendation;
    }
    
    /**
     * 更新连接状态
     */
    updateConnectionStatus(status, type) {
        this.elements.connectionStatus.innerHTML = `
            <i class="fas fa-circle"></i>
            <span>${status}</span>
        `;
        
        // 移除所有状态类
        this.elements.connectionStatus.classList.remove('connected', 'disconnected', 'connecting', 'error', 'demo');
        
        // 添加新的状态类
        if (type) {
            this.elements.connectionStatus.classList.add(type);
        }
        
        // 根据连接状态启用/禁用控制按钮
        const isConnected = type === 'connected';
        if (!isConnected && this.isRunning) {
            // 如果连接断开且正在运行，自动停止
            this.stopCommentary();
        }
    }
    
    /**
     * 更新Agent状态
     */
    updateAgentStatus(elementId, status) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.textContent = this.t(status);
        element.classList.remove('online', 'offline');
        element.classList.add(status);
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.nhlClient = new NHLCommentaryClient();
}); 