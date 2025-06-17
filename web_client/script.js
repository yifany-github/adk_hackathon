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
            gameSelect: document.getElementById('gameSelect'),
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
            dataAgentStatus: document.getElementById('dataAgentStatus'),
            commentaryAgentStatus: document.getElementById('commentaryAgentStatus'),
            audioAgentStatus: document.getElementById('audioAgentStatus')
        };
        
        this.initializeEventListeners();
        this.initializeAudioPlayer();
        this.initializeLanguage();
        this.initializeStatus();
        this.connectWebSocket();
    }
    
    /**
     * 初始化事件监听器
     */
    initializeEventListeners() {
        // 控制按钮
        this.elements.startBtn.addEventListener('click', () => this.startCommentary());
        this.elements.stopBtn.addEventListener('click', () => this.stopCommentary());
        this.elements.pauseBtn.addEventListener('click', () => this.pauseCommentary());
        
        // 音频控制
        this.elements.muteBtn.addEventListener('click', () => this.toggleMute());
        this.elements.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        
        // 语言切换
        this.elements.languageSelect.addEventListener('change', (e) => this.changeLanguage(e.target.value));
        
        // 音频播放器事件
        this.elements.audioPlayer.addEventListener('ended', () => this.playNextAudio());
        this.elements.audioPlayer.addEventListener('loadstart', () => this.updateAudioStatus('加载中...'));
        this.elements.audioPlayer.addEventListener('canplay', () => this.updateAudioStatus('准备播放'));
        this.elements.audioPlayer.addEventListener('playing', () => this.updateAudioStatus('播放中'));
        this.elements.audioPlayer.addEventListener('pause', () => this.updateAudioStatus('已暂停'));
        this.elements.audioPlayer.addEventListener('error', () => this.updateAudioStatus('播放错误'));
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }
    
    /**
     * 键盘快捷键处理
     */
    handleKeyboardShortcuts(event) {
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case ' ': // Ctrl+Space: 开始/暂停
                    event.preventDefault();
                    if (this.isRunning) {
                        this.pauseCommentary();
                    } else {
                        this.startCommentary();
                    }
                    break;
                case 's': // Ctrl+S: 停止
                    event.preventDefault();
                    this.stopCommentary();
                    break;
                case 'm': // Ctrl+M: 静音
                    event.preventDefault();
                    this.toggleMute();
                    break;
            }
        }
    }
    
    /**
     * 初始化音频播放器
     */
    initializeAudioPlayer() {
        // 设置初始音量
        this.elements.audioPlayer.volume = this.elements.volumeSlider.value / 100;
        this.updateAudioStatus(this.t('noAudio'));
    }
    
    /**
     * 初始化多语言
     */
    initializeLanguage() {
        // 设置语言选择器的值
        this.elements.languageSelect.value = this.languageManager.getCurrentLanguage();
        
        // 更新页面内容
        this.languageManager.updatePageContent();
        
        // 监听语言变化事件
        window.addEventListener('languageChanged', () => {
            this.updateDynamicContent();
        });
    }
    
    /**
     * 切换语言
     */
    changeLanguage(language) {
        this.languageManager.switchLanguage(language);
    }
    
    /**
     * 获取翻译文本
     */
    t(key) {
        return this.languageManager.t(key);
    }
    
    /**
     * 初始化状态显示
     */
    initializeStatus() {
        // 设置初始连接状态
        this.updateConnectionStatus(this.t('connecting'), 'connecting');
        
        // 设置初始Agent状态
        this.updateAgentStatus('dataAgentStatus', 'offline');
        this.updateAgentStatus('commentaryAgentStatus', 'offline');
        this.updateAgentStatus('audioAgentStatus', 'offline');
    }
    
    /**
     * 更新动态内容（不在HTML中的文本）
     */
    updateDynamicContent() {
        // 更新状态文本
        if (this.elements.audioStatus.textContent.includes('音频') || 
            this.elements.audioStatus.textContent.includes('Audio')) {
            this.updateAudioStatus(this.t('noAudio'));
        }
        
        // 更新队列占位符
        const queuePlaceholder = document.querySelector('.queue-placeholder');
        if (queuePlaceholder && this.audioQueue.length === 0) {
            queuePlaceholder.textContent = this.t('noAudioFiles');
        }
        
        // 更新历史记录占位符
        if (this.commentaryHistory.length === 0) {
            this.updateCommentaryHistory();
        }
        
        // 更新连接状态（如果已设置）
        const connectionStatus = this.elements.connectionStatus;
        const statusText = connectionStatus.querySelector('span').textContent;
        
        if (statusText.includes('已连接') || statusText.includes('Connected')) {
            this.updateConnectionStatus(this.t('connected'), 'connected');
        } else if (statusText.includes('连接断开') || statusText.includes('Disconnected')) {
            this.updateConnectionStatus(this.t('disconnected'), 'disconnected');
        } else if (statusText.includes('连接错误') || statusText.includes('Connection Error')) {
            this.updateConnectionStatus(this.t('connectionError'), 'error');
        } else if (statusText.includes('演示模式') || statusText.includes('Demo Mode')) {
            this.updateConnectionStatus(this.t('demoMode'), 'demo');
        } else if (statusText.includes('连接中') || statusText.includes('Connecting')) {
            this.updateConnectionStatus(this.t('connecting'), 'connecting');
        }
        
        // 更新Agent状态
        ['dataAgentStatus', 'commentaryAgentStatus', 'audioAgentStatus'].forEach(agentId => {
            const element = this.elements[agentId];
            if (element) {
                const currentStatus = element.className.includes('online') ? 'online' : 'offline';
                this.updateAgentStatus(agentId, currentStatus);
            }
        });
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
                // 如果Socket.IO不可用，启动演示模式
                console.log('Socket.IO不可用，启动演示模式');
                this.startDemoMode();
            }
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateConnectionStatus(this.t('connectionError'), 'error');
            
            // 模拟模式：使用假数据进行演示
            this.startDemoMode();
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
     * 原始WebSocket连接方法（备用）
     */
    connectWebSocketRaw() {
        try {
            // 根据当前协议选择WebSocket协议
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket连接已建立');
                this.updateConnectionStatus(this.t('connected'), 'connected');
                this.updateAgentStatus('dataAgentStatus', 'online');
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event.data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket连接已关闭');
                this.updateConnectionStatus(this.t('disconnected'), 'disconnected');
                this.updateAgentStatus('dataAgentStatus', 'offline');
                this.updateAgentStatus('commentaryAgentStatus', 'offline');
                this.updateAgentStatus('audioAgentStatus', 'offline');
                
                // 5秒后尝试重连
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.updateConnectionStatus(this.t('connectionError'), 'error');
            };
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateConnectionStatus(this.t('connectionError'), 'error');
            
            // 模拟模式：使用假数据进行演示
            this.startDemoMode();
        }
    }
    
    /**
     * 处理WebSocket消息
     */
    handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'commentary':
                    this.handleCommentaryUpdate(message.data);
                    break;
                case 'audio':
                    this.handleAudioUpdate(message.data);
                    break;
                case 'gameData':
                    this.handleGameDataUpdate(message.data);
                    break;
                case 'agentStatus':
                    this.handleAgentStatusUpdate(message.data);
                    break;
                case 'error':
                    this.handleError(message.data);
                    break;
                default:
                    console.log('未知消息类型:', message.type);
            }
        } catch (error) {
            console.error('解析WebSocket消息失败:', error);
        }
    }
    
    /**
     * 开始解说模式
     */
    startDemoMode() {
        console.log('启动演示模式');
        this.updateConnectionStatus(this.t('demoMode'), 'demo');
        
        // 模拟解说数据
        setTimeout(() => {
            this.simulateCommentary();
        }, 2000);
    }
    
    /**
     * 模拟解说数据（用于演示）
     */
    simulateCommentary() {
        const currentLang = this.languageManager.getCurrentLanguage();
        
        let demoCommentaries, demoGameData;
        
        if (currentLang === 'en-US') {
            demoCommentaries = [
                "Game on! Toronto Maple Leafs vs Boston Bruins, this is going to be an exciting matchup!",
                "McDavid with the puck, blazing speed down the ice!",
                "He shoots! The goalie makes a spectacular save!",
                "GOAL!!! Toronto Maple Leafs strike first!",
                "What an incredible goal! The crowd is on their feet with thunderous applause!"
            ];
            
            demoGameData = {
                homeTeam: { name: "Toronto Maple Leafs", score: 1 },
                awayTeam: { name: "Boston Bruins", score: 0 },
                period: "1st Period",
                time: "15:23",
                lastEvent: "Goal - Connor McDavid"
            };
        } else {
            demoCommentaries = [
                "比赛开始！多伦多枫叶队对阵波士顿棕熊队，这将是一场激动人心的较量！",
                "McDavid控球推进，他的速度令人惊叹！",
                "射门！门将做出了精彩的扑救！",
                "进球！！！多伦多枫叶队率先得分！",
                "这是一个令人难以置信的进球，现场观众爆发出热烈的掌声！"
            ];
            
            demoGameData = {
                homeTeam: { name: "多伦多枫叶队", score: 1 },
                awayTeam: { name: "波士顿棕熊队", score: 0 },
                period: "第1节",
                time: "15:23",
                lastEvent: "进球 - Connor McDavid"
            };
        }
        
        let commentaryIndex = 0;
        
        const interval = setInterval(() => {
            if (!this.isRunning || commentaryIndex >= demoCommentaries.length) {
                clearInterval(interval);
                return;
            }
            
            const commentary = demoCommentaries[commentaryIndex];
            this.addCommentary(commentary);
            this.addToAudioQueue({
                text: commentary,
                style: this.elements.voiceStyle.value,
                url: this.generateDemoAudioUrl(commentary)
            });
            
            // 更新比赛数据
            if (commentaryIndex === 3) { // 进球时更新比分
                this.updateGameData(demoGameData);
            }
            
            commentaryIndex++;
        }, 3000);
    }
    
    /**
     * 生成演示音频URL
     */
    generateDemoAudioUrl(text) {
        // 这里应该是实际的音频生成逻辑
        // 为了演示，我们使用一个占位符
        return `data:audio/wav;base64,${btoa(text)}`;
    }
    
    /**
     * 开始解说
     */
    startCommentary() {
        const gameId = this.elements.gameSelect.value;
        if (!gameId) {
            alert(this.t('pleaseSelectGameFirst'));
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
            // 演示模式
            this.simulateCommentary();
        }
        
        console.log(`开始解说比赛: ${gameId}`);
    }
    
    /**
     * 停止解说
     */
    stopCommentary() {
        this.isRunning = false;
        this.isPaused = false;
        this.currentGameId = null;
        
        // 更新UI状态
        this.elements.startBtn.disabled = false;
        this.elements.stopBtn.disabled = true;
        this.elements.pauseBtn.disabled = true;
        this.elements.pauseBtn.innerHTML = `<i class="fas fa-pause"></i> ${this.t('pauseCommentary')}`;
        this.elements.commentaryStatus.textContent = this.t('stopped');
        
        // 停止音频播放
        this.elements.audioPlayer.pause();
        this.clearAudioQueue();
        
        // 发送停止命令到后端
        if (this.websocket && this.websocket.connected) {
            this.sendMessage('stop', {});
        }
        
        console.log('解说已停止');
    }
    
    /**
     * 暂停/恢复解说
     */
    pauseCommentary() {
        if (!this.isRunning) return;
        
        this.isPaused = !this.isPaused;
        
        if (this.isPaused) {
            this.elements.pauseBtn.innerHTML = `<i class="fas fa-play"></i> ${this.t('resumeCommentary')}`;
            this.elements.commentaryStatus.textContent = this.t('paused');
            this.elements.audioPlayer.pause();
        } else {
            this.elements.pauseBtn.innerHTML = `<i class="fas fa-pause"></i> ${this.t('pauseCommentary')}`;
            this.elements.commentaryStatus.textContent = this.t('commentating');
            if (this.audioQueue.length > 0) {
                this.elements.audioPlayer.play();
            }
        }
        
        // 发送暂停/恢复命令到后端
        if (this.websocket && this.websocket.connected) {
            this.sendMessage(this.isPaused ? 'pause' : 'resume', {});
        }
        
        console.log(this.isPaused ? '解说已暂停' : '解说已恢复');
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
        Object.keys(data).forEach(agentType => {
            this.updateAgentStatus(`${agentType}Status`, data[agentType]);
        });
    }
    
    /**
     * 处理错误
     */
    handleError(error) {
        console.error('后端错误:', error);
        alert(`错误: ${error.message}`);
    }
    
    /**
     * 添加解说到界面
     */
    addCommentary(text) {
        // 更新当前解说
        this.elements.currentCommentary.innerHTML = `
            <div class="commentary-text">${text}</div>
        `;
        
        // 添加到历史记录
        const timestamp = new Date().toLocaleTimeString();
        this.commentaryHistory.unshift({ text, timestamp });
        
        // 限制历史记录数量
        if (this.commentaryHistory.length > 20) {
            this.commentaryHistory = this.commentaryHistory.slice(0, 20);
        }
        
        this.updateCommentaryHistory();
    }
    
    /**
     * 更新解说历史记录
     */
    updateCommentaryHistory() {
        const historyContainer = this.elements.commentaryHistory.querySelector('.history-list');
        
        if (this.commentaryHistory.length === 0) {
            historyContainer.innerHTML = `<div class="queue-placeholder">${this.t('noCommentaryHistory')}</div>`;
            return;
        }
        
        historyContainer.innerHTML = this.commentaryHistory.map(item => `
            <div class="history-item">
                <div class="timestamp">${item.timestamp}</div>
                <div class="text">${item.text}</div>
            </div>
        `).join('');
    }
    
    /**
     * 添加音频到播放队列
     */
    addToAudioQueue(audioData) {
        this.audioQueue.push(audioData);
        this.updateAudioQueueDisplay();
        
        // 如果当前没有播放音频，开始播放
        if (this.elements.audioPlayer.paused && !this.isPaused) {
            this.playNextAudio();
        }
    }
    
    /**
     * 播放下一个音频
     */
    playNextAudio() {
        if (this.audioQueue.length === 0 || this.isPaused) {
            this.updateAudioStatus(this.t('noAudio'));
            return;
        }
        
        const audioData = this.audioQueue.shift();
        this.elements.audioPlayer.src = audioData.url;
        this.elements.audioPlayer.load();
        
        this.elements.audioPlayer.play().then(() => {
            this.showAudioNotification(`${this.t('playing')}: ${audioData.text.substring(0, 30)}...`);
        }).catch(error => {
            console.error('音频播放失败:', error);
            this.updateAudioStatus(this.t('audioError'));
        });
        
        this.updateAudioQueueDisplay();
    }
    
    /**
     * 更新音频队列显示
     */
    updateAudioQueueDisplay() {
        const queueContainer = this.elements.audioQueue;
        
        if (this.audioQueue.length === 0) {
            queueContainer.innerHTML = `<div class="queue-placeholder">${this.t('noAudioFiles')}</div>`;
            return;
        }
        
        queueContainer.innerHTML = this.audioQueue.map((item, index) => `
            <div class="queue-item ${index === 0 ? 'playing' : ''}">
                <span>${item.text.substring(0, 40)}...</span>
                <small>${item.style}</small>
            </div>
        `).join('');
    }
    
    /**
     * 清空音频队列
     */
    clearAudioQueue() {
        this.audioQueue = [];
        this.currentAudioIndex = 0;
        this.updateAudioQueueDisplay();
    }
    
    /**
     * 切换静音
     */
    toggleMute() {
        const isMuted = this.elements.audioPlayer.muted;
        this.elements.audioPlayer.muted = !isMuted;
        
        const icon = this.elements.muteBtn.querySelector('i');
        icon.className = isMuted ? 'fas fa-volume-up' : 'fas fa-volume-mute';
        
        this.updateAudioStatus(isMuted ? this.t('unmuted') : this.t('muted'));
    }
    
    /**
     * 设置音量
     */
    setVolume(value) {
        this.elements.audioPlayer.volume = value / 100;
        this.updateAudioStatus(`${this.t('volume')}: ${value}%`);
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
        const notification = this.elements.audioNotification;
        const span = notification.querySelector('span');
        span.textContent = message;
        
        notification.classList.add('show');
        
        setTimeout(() => {
            notification.classList.remove('show');
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
                    <span class="team-name">${data.homeTeam.name}</span>
                    <span class="team-score">${data.homeTeam.score}</span>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <span class="team-name">${data.awayTeam.name}</span>
                    <span class="team-score">${data.awayTeam.score}</span>
                </div>
            `;
        }
        
        // 更新比赛状态
        if (data.period && data.time) {
            this.elements.gameStatus.innerHTML = `
                <div class="period">${data.period}</div>
                <div class="time">${data.time}</div>
            `;
        }
        
        // 更新最新事件
        if (data.lastEvent) {
            this.elements.recentEvents.innerHTML = `
                <div class="event-item">
                    <div class="event-time">${new Date().toLocaleTimeString()}</div>
                    <div class="event-description">${data.lastEvent}</div>
                </div>
            `;
        }
    }
    
    /**
     * 更新连接状态
     */
    updateConnectionStatus(status, type) {
        const statusElement = this.elements.connectionStatus;
        const span = statusElement.querySelector('span');
        const icon = statusElement.querySelector('i');
        
        span.textContent = status;
        
        // 清除所有状态类
        statusElement.classList.remove('connected', 'connecting', 'disconnected', 'error', 'demo');
        
        // 添加新状态类
        if (type) {
            statusElement.classList.add(type);
        }
        
        // 更新图标
        switch (type) {
            case 'connected':
                icon.className = 'fas fa-circle';
                break;
            case 'connecting':
                icon.className = 'fas fa-circle';
                break;
            case 'disconnected':
            case 'error':
                icon.className = 'fas fa-circle';
                break;
            case 'demo':
                icon.className = 'fas fa-play-circle';
                break;
            default:
                icon.className = 'fas fa-circle';
        }
    }
    
    /**
     * 更新Agent状态
     */
    updateAgentStatus(elementId, status) {
        const element = this.elements[elementId];
        if (!element) return;
        
        element.textContent = status === 'online' ? this.t('online') : this.t('offline');
        element.className = `status-indicator ${status}`;
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.nhlClient = new NHLCommentaryClient();
    console.log('NHL Commentary Client 已初始化');
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (window.nhlClient && window.nhlClient.websocket) {
        window.nhlClient.websocket.close();
    }
}); 