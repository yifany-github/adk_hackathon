# Google Cloud 部署指南

## 🎯 部署方案概述

您的NHL Live Commentary项目支持三种Google Cloud部署方案：

1. **Google App Engine**（推荐）- 最简单，无需管理服务器
2. **Google Cloud Run** - 容器化部署，灵活扩展
3. **Google Compute Engine** - 完全控制的虚拟机

## 📋 前置准备

### 1. 安装Google Cloud SDK

```bash
# macOS (使用 Homebrew)
brew install --cask google-cloud-sdk

# 或者直接下载安装
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 2. 项目初始化

```bash
# 登录Google Cloud
gcloud auth login

# 创建新项目或选择现有项目
gcloud projects create nhl-commentary-2024 --name="NHL Live Commentary"

# 设置项目ID
gcloud config set project nhl-commentary-2024

# 启用必要的API
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

## 🚀 方案一：Google App Engine 部署（推荐）

### 步骤1：验证配置文件

您的`app.yaml`已经配置好，包含：
- Python 3.9 运行环境
- 自动扩容配置（最多10个实例）
- 资源配置（2 CPU, 4GB内存）
- 静态文件处理

### 步骤2：设置环境变量

在`app.yaml`中添加API密钥：

```yaml
env_variables:
  FLASK_ENV: production
  GEMINI_API_KEY: "your_gemini_api_key_here"
  GOOGLE_API_KEY: "your_google_api_key_here"
```

### 步骤3：部署应用

```bash
# 切换到项目目录
cd /Users/yifan/Downloads/google_hackathon/adk_hackathon/web_client_demo

# 部署到App Engine
gcloud app deploy app.yaml

# 查看部署的应用
gcloud app browse
```

### 步骤4：管理部署

```bash
# 查看日志
gcloud app logs tail -s nhl-commentary

# 查看应用信息
gcloud app describe

# 停止应用（节省费用）
gcloud app versions stop VERSION_ID
```

## 🐳 方案二：Google Cloud Run 部署

### 步骤1：构建容器镜像

```bash
# 在项目根目录执行
cd /Users/yifan/Downloads/google_hackathon/adk_hackathon

# 构建并推送镜像
gcloud builds submit web_client_demo/ --tag gcr.io/nhl-commentary-2024/nhl-commentary
```

### 步骤2：部署到Cloud Run

```bash
# 部署服务
gcloud run deploy nhl-commentary \
  --image gcr.io/nhl-commentary-2024/nhl-commentary \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 10 \
  --set-env-vars FLASK_ENV=production,GEMINI_API_KEY=your_key,GOOGLE_API_KEY=your_key

# 获取服务URL
gcloud run services describe nhl-commentary \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'
```

## 💻 方案三：Google Compute Engine 部署

### 步骤1：创建虚拟机

```bash
# 创建VM实例
gcloud compute instances create nhl-commentary-vm \
  --image-family ubuntu-2004-lts \
  --image-project ubuntu-os-cloud \
  --machine-type e2-standard-4 \
  --zone us-central1-a \
  --tags http-server,https-server \
  --boot-disk-size 50GB

# 配置防火墙规则
gcloud compute firewall-rules create allow-http-8080 \
  --allow tcp:8080 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server
```

### 步骤2：配置虚拟机

```bash
# SSH连接到VM
gcloud compute ssh nhl-commentary-vm --zone us-central1-a

# 在VM中执行以下命令：

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python和依赖
sudo apt install -y python3 python3-pip git nginx supervisor

# 克隆项目
git clone https://github.com/your-username/adk_hackathon.git
cd adk_hackathon/web_client_demo

# 安装Python依赖
pip3 install -r requirements.txt

# 设置环境变量
echo "export GEMINI_API_KEY=your_gemini_api_key" >> ~/.bashrc
echo "export GOOGLE_API_KEY=your_google_api_key" >> ~/.bashrc
source ~/.bashrc
```

### 步骤3：配置Nginx和Supervisor

创建Nginx配置：
```bash
sudo nano /etc/nginx/sites-available/nhl-commentary
```

```nginx
server {
    listen 80;
    server_name your-vm-external-ip;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/nhl-commentary /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔧 API密钥配置

### 获取API密钥

1. **Gemini API Key**：
   - 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
   - 创建新的API密钥

2. **Google API Key**：
   - 访问 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - 创建API密钥并启用Text-to-Speech API

### 安全配置

对于生产环境，建议使用Google Secret Manager：

```bash
# 创建密钥
gcloud secrets create gemini-api-key --data-file=-
gcloud secrets create google-api-key --data-file=-

# 在app.yaml中引用（App Engine）
env_variables:
  GEMINI_API_KEY: ${sm://gemini-api-key}
  GOOGLE_API_KEY: ${sm://google-api-key}
```

## 📊 监控和日志

### 查看应用日志

```bash
# App Engine日志
gcloud app logs tail -s nhl-commentary

# Cloud Run日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=nhl-commentary" --limit 50

# Compute Engine日志
gcloud compute ssh nhl-commentary-vm --zone us-central1-a --command "tail -f /var/log/supervisor/nhl-commentary.log"
```

### 性能监控

在Google Cloud Console中：
1. 访问"监控"部分
2. 创建自定义仪表板
3. 监控CPU、内存、请求延迟等指标

## 💰 成本优化

### App Engine
- 使用基本扩容而非自动扩容
- 设置合理的空闲超时时间
- 定期停止未使用的版本

### Cloud Run
- 设置最小实例数为0
- 使用并发设置优化实例利用率
- 监控冷启动时间

### Compute Engine
- 使用抢占式实例降低成本
- 根据使用模式调整实例大小
- 设置自动关机策略

## 🔍 故障排除

### 常见问题

1. **部署失败**：
   ```bash
   # 检查构建日志
   gcloud app logs tail -s default
   ```

2. **API密钥错误**：
   - 确保密钥格式正确
   - 检查API配额限制
   - 验证服务已启用

3. **内存不足**：
   - 增加实例内存配置
   - 优化代码内存使用
   - 使用更大的机器类型

4. **超时错误**：
   - 增加请求超时时间
   - 优化处理逻辑
   - 使用异步处理

## 📞 技术支持

如果遇到部署问题：
1. 检查Google Cloud状态页面
2. 查看详细错误日志
3. 参考Google Cloud文档
4. 联系技术支持团队

---

**推荐部署方案**：Google App Engine，因为它配置最简单，自动处理扩容，并且已经有完整的配置文件。 