#!/bin/bash

# NHL Live Commentary - Google Cloud 部署脚本
# 使用方法: ./deploy.sh [app-engine|cloud-run|setup]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查部署依赖..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "Google Cloud SDK 未安装。请先安装: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    log_success "Google Cloud SDK 已安装"
}

# 项目设置
setup_project() {
    log_info "设置Google Cloud项目..."
    
    # 检查是否已登录
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null; then
        log_info "请先登录Google Cloud..."
        gcloud auth login
    fi
    
    # 设置项目ID
    read -p "请输入您的Google Cloud项目ID（或按回车使用 nhl-commentary-2024）: " PROJECT_ID
    PROJECT_ID=${PROJECT_ID:-nhl-commentary-2024}
    
    log_info "设置项目: $PROJECT_ID"
    gcloud config set project $PROJECT_ID
    
    # 创建项目（如果不存在）
    if ! gcloud projects describe $PROJECT_ID &>/dev/null; then
        log_info "创建新项目: $PROJECT_ID"
        gcloud projects create $PROJECT_ID --name="NHL Live Commentary"
    fi
    
    # 启用必要的API
    log_info "启用必要的Google Cloud APIs..."
    gcloud services enable appengine.googleapis.com --quiet
    gcloud services enable cloudbuild.googleapis.com --quiet
    gcloud services enable run.googleapis.com --quiet
    gcloud services enable secretmanager.googleapis.com --quiet
    
    log_success "项目设置完成"
}

# API密钥配置
configure_api_keys() {
    log_info "配置API密钥..."
    
    # 读取API密钥
    read -p "请输入Gemini API Key (按回车跳过): " GEMINI_KEY
    read -p "请输入Google API Key (按回车跳过): " GOOGLE_KEY
    
    if [ ! -z "$GEMINI_KEY" ] || [ ! -z "$GOOGLE_KEY" ]; then
        # 更新app.yaml中的环境变量
        cp app.yaml app.yaml.backup
        
        # 创建临时文件包含API密钥
        cat >> app.yaml << EOF

# API Keys Configuration (added by deploy script)
env_variables:
  FLASK_ENV: production
EOF
        
        if [ ! -z "$GEMINI_KEY" ]; then
            echo "  GEMINI_API_KEY: \"$GEMINI_KEY\"" >> app.yaml
        fi
        
        if [ ! -z "$GOOGLE_KEY" ]; then
            echo "  GOOGLE_API_KEY: \"$GOOGLE_KEY\"" >> app.yaml
        fi
        
        log_success "API密钥已添加到app.yaml"
    else
        log_warning "跳过API密钥配置，您可以稍后在web界面中配置"
    fi
}

# App Engine部署
deploy_app_engine() {
    log_info "开始App Engine部署..."
    
    # 检查app.yaml
    if [ ! -f "app.yaml" ]; then
        log_error "未找到app.yaml文件"
        exit 1
    fi
    
    # 配置API密钥
    configure_api_keys
    
    # 初始化App Engine（如果需要）
    if ! gcloud app describe &>/dev/null; then
        log_info "初始化App Engine..."
        gcloud app create --region=us-central
    fi
    
    # 部署应用
    log_info "部署应用到App Engine..."
    gcloud app deploy app.yaml --quiet
    
    # 获取应用URL
    APP_URL=$(gcloud app browse --no-launch-browser 2>&1 | grep -o 'https://[^[:space:]]*')
    
    log_success "App Engine部署完成！"
    log_info "应用URL: $APP_URL"
    
    # 恢复原始app.yaml（如果有备份）
    if [ -f "app.yaml.backup" ]; then
        mv app.yaml.backup app.yaml
        log_info "已恢复原始app.yaml文件"
    fi
}

# Cloud Run部署
deploy_cloud_run() {
    log_info "开始Cloud Run部署..."
    
    # 检查Dockerfile
    if [ ! -f "Dockerfile" ]; then
        log_error "未找到Dockerfile文件"
        exit 1
    fi
    
    # 获取项目ID
    PROJECT_ID=$(gcloud config get-value project)
    
    # 构建镜像
    log_info "构建Docker镜像..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/nhl-commentary .
    
    # 部署到Cloud Run
    log_info "部署到Cloud Run..."
    
    # 读取API密钥（可选）
    read -p "请输入Gemini API Key (按回车跳过): " GEMINI_KEY
    read -p "请输入Google API Key (按回车跳过): " GOOGLE_KEY
    
    # 构建环境变量参数
    ENV_VARS="FLASK_ENV=production"
    if [ ! -z "$GEMINI_KEY" ]; then
        ENV_VARS="$ENV_VARS,GEMINI_API_KEY=$GEMINI_KEY"
    fi
    if [ ! -z "$GOOGLE_KEY" ]; then
        ENV_VARS="$ENV_VARS,GOOGLE_API_KEY=$GOOGLE_KEY"
    fi
    
    gcloud run deploy nhl-commentary \
        --image gcr.io/$PROJECT_ID/nhl-commentary \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --memory 4Gi \
        --cpu 2 \
        --timeout 3600 \
        --max-instances 10 \
        --set-env-vars "$ENV_VARS" \
        --quiet
    
    # 获取服务URL
    SERVICE_URL=$(gcloud run services describe nhl-commentary \
        --platform managed \
        --region us-central1 \
        --format 'value(status.url)')
    
    log_success "Cloud Run部署完成！"
    log_info "服务URL: $SERVICE_URL"
}

# 清理资源
cleanup() {
    log_info "清理部署资源..."
    
    read -p "是否要删除所有部署的资源？(y/N): " CONFIRM
    if [[ $CONFIRM =~ ^[Yy]$ ]]; then
        # 删除App Engine版本
        gcloud app versions list --format="value(version.id)" | xargs -I {} gcloud app versions delete {} --quiet
        
        # 删除Cloud Run服务
        gcloud run services delete nhl-commentary --platform managed --region us-central1 --quiet
        
        log_success "资源清理完成"
    fi
}

# 主函数
main() {
    echo "==============================================="
    echo "🏒 NHL Live Commentary - Google Cloud 部署工具"
    echo "==============================================="
    echo
    
    case "${1:-}" in
        "setup")
            check_dependencies
            setup_project
            ;;
        "app-engine")
            check_dependencies
            deploy_app_engine
            ;;
        "cloud-run")
            check_dependencies
            deploy_cloud_run
            ;;
        "cleanup")
            cleanup
            ;;
        *)
            echo "使用方法: $0 [setup|app-engine|cloud-run|cleanup]"
            echo
            echo "命令说明:"
            echo "  setup      - 初始化Google Cloud项目和API"
            echo "  app-engine - 部署到Google App Engine (推荐)"
            echo "  cloud-run  - 部署到Google Cloud Run"
            echo "  cleanup    - 清理部署的资源"
            echo
            echo "推荐部署流程:"
            echo "  1. ./deploy.sh setup"
            echo "  2. ./deploy.sh app-engine"
            echo
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 