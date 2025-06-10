#!/usr/bin/env python3
"""
配置Gemini API Key的脚本
"""

import os
import sys

def setup_api_key():
    """配置API Key"""
    print("🔑 Gemini API Key 配置助手")
    print("=" * 40)
    
    # 检查当前是否已配置
    current_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
    if current_key:
        print(f"✅ 检测到已配置的API Key: {current_key[:10]}...")
        choice = input("\n是否要更新API Key? (y/N): ").strip().lower()
        if choice != 'y':
            print("✅ 保持当前配置")
            return current_key
    
    print("\n📝 请输入您的Gemini API Key:")
    print("💡 您可以在这里获取: https://aistudio.google.com/app/apikey")
    
    api_key = input("\nAPI Key: ").strip()
    
    if not api_key:
        print("❌ API Key不能为空")
        return None
    
    if len(api_key) < 30:
        print("⚠️ API Key长度似乎太短，请检查是否正确")
        choice = input("是否继续? (y/N): ").strip().lower()
        if choice != 'y':
            return None
    
    # 设置环境变量的几种方式
    print("\n🔧 配置方法选择:")
    print("1. 临时设置 (仅当前会话有效)")
    print("2. 永久设置 (添加到 ~/.zshrc)")
    print("3. 创建 .env 文件")
    
    choice = input("\n选择方法 (1-3): ").strip()
    
    if choice == "1":
        # 临时设置
        os.environ['GEMINI_API_KEY'] = api_key
        print("✅ API Key已临时设置")
        print("💡 要在新终端中使用，请运行:")
        print(f"   export GEMINI_API_KEY='{api_key}'")
        
    elif choice == "2":
        # 永久设置到 ~/.zshrc
        zshrc_path = os.path.expanduser("~/.zshrc")
        try:
            with open(zshrc_path, 'a') as f:
                f.write(f"\n# Gemini API Key for NHL Audio Agent\n")
                f.write(f"export GEMINI_API_KEY='{api_key}'\n")
            
            print(f"✅ API Key已添加到 {zshrc_path}")
            print("💡 请运行以下命令使配置生效:")
            print("   source ~/.zshrc")
            print("或重新打开终端")
            
            # 同时临时设置
            os.environ['GEMINI_API_KEY'] = api_key
            
        except Exception as e:
            print(f"❌ 写入 .zshrc 失败: {e}")
            return None
            
    elif choice == "3":
        # 创建 .env 文件
        env_path = ".env"
        try:
            # 检查是否已存在 .env 文件
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    content = f.read()
                
                # 更新现有的GEMINI_API_KEY或添加新的
                lines = content.split('\n')
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith('GEMINI_API_KEY=') or line.startswith('GOOGLE_AI_API_KEY='):
                        lines[i] = f'GEMINI_API_KEY={api_key}'
                        updated = True
                        break
                
                if not updated:
                    lines.append(f'GEMINI_API_KEY={api_key}')
                
                content = '\n'.join(lines)
            else:
                content = f'# NHL Audio Agent Configuration\nGEMINI_API_KEY={api_key}\n'
            
            with open(env_path, 'w') as f:
                f.write(content)
            
            print(f"✅ API Key已保存到 {env_path}")
            print("💡 项目会自动加载这个文件")
            
            # 同时临时设置
            os.environ['GEMINI_API_KEY'] = api_key
            
        except Exception as e:
            print(f"❌ 创建 .env 文件失败: {e}")
            return None
            
    else:
        print("❌ 无效选择")
        return None
    
    return api_key

def test_api_key():
    """测试API Key是否有效"""
    print("\n🧪 测试API Key...")
    
    try:
        from google import genai
        
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
        if not api_key:
            print("❌ 未找到API Key")
            return False
        
        # 创建客户端并测试
        client = genai.Client(api_key=api_key)
        
        # 尝试列出模型来验证API Key
        models = list(client.models.list())
        print(f"✅ API Key有效! 可用模型数量: {len(models)}")
        
        # 检查是否支持TTS
        tts_models = [m for m in models if 'tts' in m.name.lower()]
        if tts_models:
            print(f"✅ 支持TTS功能，找到TTS模型: {len(tts_models)}个")
        else:
            print("⚠️ 未找到专门的TTS模型，但可能仍然支持音频生成")
        
        return True
        
    except ImportError:
        print("❌ google-genai库未安装")
        print("💡 请运行: pip install google-genai")
        return False
        
    except Exception as e:
        print(f"❌ API Key测试失败: {e}")
        print("💡 请检查API Key是否正确")
        return False

def main():
    """主函数"""
    try:
        # 配置API Key
        api_key = setup_api_key()
        
        if api_key:
            # 测试API Key
            if test_api_key():
                print("\n🎉 配置完成！现在可以使用真实的Gemini TTS了")
                print("\n下一步:")
                print("1. 运行: python test_audio_generation.py")
                print("2. 或运行: python examples/audio_agent_demo.py")
            else:
                print("\n⚠️ API Key配置完成，但测试失败")
                print("请检查API Key是否正确")
        else:
            print("\n❌ API Key配置失败")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户取消配置")
    except Exception as e:
        print(f"\n❌ 配置过程中出错: {e}")

if __name__ == "__main__":
    main() 