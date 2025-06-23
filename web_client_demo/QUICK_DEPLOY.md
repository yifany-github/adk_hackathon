# 🚀 Google Cloud 快速部署指南

## 一键部署（推荐）

使用我们提供的自动化脚本，只需3个命令即可完成部署：

```bash
# 1. 进入部署目录
cd web_client_demo

# 2. 设置Google Cloud项目
./deploy.sh setup

# 3. 部署到App Engine
./deploy.sh app-engine
```

## 📋 前置要求

1. **Google Cloud账户**：访问 [Google Cloud Console](https://console.cloud.google.com/)
2. **启用计费**：确保您的Google Cloud项目已启用计费
3. **API密钥**：
   - Gemini API Key：[获取地址](https://makersuite.google.com/app/apikey)
   - Google API Key：[获取地址](https://console.cloud.google.com/apis/credentials)

## 🛠 手动部署步骤

### 方法一：Google App Engine（最简单）

```bash
# 1. 安装Google Cloud SDK
brew install --cask google-cloud-sdk

# 2. 登录并设置项目
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. 启用API
gcloud services enable appengine.googleapis.com

# 4. 创建App Engine应用
gcloud app create --region=us-central

# 5. 部署应用
gcloud app deploy app.yaml

# 6. 查看应用
gcloud app browse
```

### 方法二：Google Cloud Run

```bash
# 1. 构建并推送镜像
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nhl-commentary

# 2. 部署到Cloud Run
gcloud run deploy nhl-commentary \
  --image gcr.io/YOUR_PROJECT_ID/nhl-commentary \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2
```

## 🔧 API密钥配置

部署完成后，您需要在web界面中配置API密钥：

1. 访问部署的应用URL
2. 点击"Settings"（设置）
3. 输入您的API密钥：
   - **Gemini API Key**：用于AI评论生成
   - **Google API Key**：用于语音合成

## 🎯 使用应用

1. **选择比赛**：从可用比赛列表中选择一个
2. **设置时长**：选择评论生成的时长（建议5-10分钟）
3. **开始评论**：点击"Start Commentary"开始生成
4. **实时监控**：查看处理进度和生成的音频文件
5. **播放音频**：点击音频文件进行播放

## 📊 费用估算

### App Engine费用（基于使用量）
- **免费额度**：每月28个前端实例小时
- **付费使用**：约$0.05-0.10/小时（基本配置）
- **建议配置**：空闲时自动缩容到0实例

### Cloud Run费用
- **免费额度**：每月200万次请求
- **付费使用**：$0.40/百万次请求
- **CPU时间**：$0.00001667/vCPU秒

## 🔍 故障排除

### 常见问题

1. **部署失败 - 权限错误**
   ```bash
   # 确保已正确登录
   gcloud auth login
   gcloud auth application-default login
   ```

2. **API密钥无效**
   - 检查密钥格式是否正确
   - 确保相关API服务已启用
   - 验证密钥权限设置

3. **内存不足错误**
   - 在`app.yaml`中增加`memory_gb`配置
   - 或者升级到更大的实例类型

4. **超时错误**
   - 检查网络连接
   - 确保数据源可访问
   - 增加请求超时时间配置

## 📞 获取帮助

如果遇到问题：
1. 查看部署日志：`gcloud app logs tail -s default`
2. 检查[完整部署指南](deploy_guide.md)
3. 参考[Google Cloud文档](https://cloud.google.com/docs)

---

**🎉 恭喜！您的NHL Live Commentary应用已成功部署到Google Cloud！** 