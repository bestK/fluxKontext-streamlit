"""
Flux Kontext Streamlit Web界面
基于Web的多图片AI编辑工具

运行方法:
pip install streamlit
streamlit run streamlit_app.py
"""

import streamlit as st
import os
import time
from PIL import Image
import io
import base64
from flux_kontext_multi_native import FluxKontextNativeMultiEditor

# 页面配置
st.set_page_config(
    page_title="🎨 Flux Kontext AI图像编辑器",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义CSS样式
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4ECDC4;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        color: #721C24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D1ECF1;
        border: 1px solid #BEE5EB;
        color: #0C5460;
    }
    .fixed-log-container {
        height: 200px;
        max-height: 200px;
        overflow-y: auto;
        background-color: #1e1e1e;
        color: #ffffff;
        border: 1px solid #404040;
        border-radius: 0.5rem;
        padding: 1rem;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.85rem;
        line-height: 1.4;
        white-space: pre-wrap;
        word-wrap: break-word;
        scroll-behavior: smooth;
        box-sizing: border-box;
    }
    .fixed-log-container::-webkit-scrollbar {
        width: 8px;
    }
    .fixed-log-container::-webkit-scrollbar-track {
        background: #2a2a2a;
        border-radius: 4px;
    }
    .fixed-log-container::-webkit-scrollbar-thumb {
        background: #555555;
        border-radius: 4px;
    }
    .fixed-log-container::-webkit-scrollbar-thumb:hover {
        background: #777777;
    }
</style>
""",
    unsafe_allow_html=True,
)


def init_session_state():
    """初始化会话状态"""
    if "editor" not in st.session_state:
        st.session_state.editor = None
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "result_image" not in st.session_state:
        st.session_state.result_image = None
    if "edit_instruction" not in st.session_state:
        st.session_state.edit_instruction = ""
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "base_url" not in st.session_state:
        st.session_state.base_url = "https://api.bfl.ai"
    if "api_configured" not in st.session_state:
        st.session_state.api_configured = False
    if "log_messages" not in st.session_state:
        st.session_state.log_messages = []
    if "log_expanded" not in st.session_state:
        st.session_state.log_expanded = True


def load_editor():
    """加载编辑器"""
    try:
        if st.session_state.editor is None:
            # 使用页面配置的API密钥和BASE_URL
            if st.session_state.api_key.strip():
                # 验证和格式化BASE_URL
                base_url = st.session_state.base_url.strip()
                if not base_url:
                    base_url = "https://api.bfl.ai"
                elif not base_url.startswith("http"):
                    base_url = f"https://{base_url}"

                # 临时创建配置文件
                config_content = f"""[API]
X_KEY = {st.session_state.api_key.strip()}
BASE_URL = {base_url}
"""
                with open("temp_config.ini", "w", encoding="utf-8") as f:
                    f.write(config_content)

                # 创建编辑器实例，指定临时配置文件
                from flux_kontext_multi_native import FluxKontextNativeMultiEditor

                st.session_state.editor = FluxKontextNativeMultiEditor(
                    config_path="temp_config.ini"
                )
                st.session_state.api_configured = True
            else:
                st.error("❌ 请先配置API密钥")
                return False
        return True
    except Exception as e:
        st.error(f"❌ 初始化失败: {str(e)}")
        if "API" in str(e) or "key" in str(e).lower():
            st.error("请检查API密钥是否正确")
        else:
            st.error("请检查网络连接和API密钥")
        return False


def create_config_section():
    """创建配置文件部分"""
    st.markdown("### ⚙️ API配置")

    # 页面直接配置API密钥
    api_key_input = st.text_input(
        "API密钥",
        value=st.session_state.api_key,
        type="password",
        placeholder="请输入您的Flux Kontext API密钥",
        help="从 https://api.bfl.ai 获取您的API密钥",
    )

    # 自定义BASE_URL配置
    base_url_input = st.text_input(
        "API服务器地址",
        value=st.session_state.base_url,
        placeholder="https://api.bfl.ai",
        help="API服务器的基础URL，支持自定义服务器",
    )

    # 检查配置是否有变化
    config_changed = False
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        config_changed = True

    if base_url_input != st.session_state.base_url:
        st.session_state.base_url = base_url_input
        config_changed = True

    if config_changed:
        st.session_state.editor = None  # 重置编辑器以使用新配置
        st.session_state.api_configured = False

    if st.session_state.api_key.strip():
        st.success("✅ API密钥已配置")

        # 显示当前BASE_URL
        current_base_url = (
            st.session_state.base_url.strip()
            if st.session_state.base_url.strip()
            else "https://api.bfl.ai"
        )
        if not current_base_url.startswith("http"):
            current_base_url = f"https://{current_base_url}"
        st.info(f"🔗 当前API服务器: {current_base_url}")

        if st.button("🧪 测试API连接"):
            with st.spinner("正在测试API连接..."):
                if load_editor():
                    st.success("🎉 API连接测试成功！")
                else:
                    st.error("❌ API连接测试失败")
    else:
        st.warning("⚠️ 请输入API密钥")

    # 显示获取API密钥的链接
    st.markdown(
        """
    **🔗 获取API密钥:**
    1. 访问 [Black Forest Labs API](https://api.bfl.ai)
    2. 注册账户并获取API密钥
    3. 将密钥粘贴到上方输入框中
    """
    )


def render_collapsible_log(key_suffix=""):
    """渲染可折叠的日志容器"""
    if not st.session_state.log_messages:
        return

    st.markdown("#### 📋 处理日志")

    # 如果展开状态，显示日志
    if st.session_state.log_expanded:
        # 显示最近的日志（限制显示条数以提高性能）
        recent_logs = st.session_state.log_messages[-15:]  # 只显示最近15条日志
        log_text = "\n".join(recent_logs)

        # HTML转义日志内容
        import html

        escaped_log_text = html.escape(log_text)

        # 创建一个带滚动的日志容器
        log_container_html = f"""
        <div style="
            height: 200px; 
            overflow-y: auto; 
            background-color: #1e1e1e; 
            color: #ffffff; 
            padding: 10px; 
            border-radius: 5px; 
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
            font-size: 0.85rem; 
            line-height: 1.4; 
            white-space: pre-wrap; 
            border: 1px solid #404040;
            ">{escaped_log_text}</div>
        """

        st.markdown(log_container_html, unsafe_allow_html=True)


def quality_presets():
    """质量预设选项"""
    presets = {
        "🎯 标准质量": {
            "keywords": "high quality, clear, sharp focus",
            "model": "flux-kontext-pro",
            "upsampling": False,
        },
        "📸 专业摄影": {
            "keywords": "Professional high-resolution studio portrait, ultra sharp focus, 8K Ultra HD, perfect lighting, studio background, crystal clear details, award-winning composition, warm and natural expression, realistic skin and fur texture, cinematic depth of field, clean and uncluttered frame, studio-quality photography",
            "model": "flux-kontext-max",
            "upsampling": True,
        },
        "🎬 电影级质量": {
            "keywords": "cinematic 4K quality, ultra-sharp details, perfect composition, dramatic lighting",
            "model": "flux-kontext-max",
            "upsampling": True,
        },
        "🏆 8K超高清": {
            "keywords": "8K ultra HD, crystal clear, pixel-perfect, masterpiece, exquisite detail",
            "model": "flux-kontext-max",
            "upsampling": True,
        },
        "🎨 艺术级": {
            "keywords": "fine art photography, museum quality, artistic composition, gallery-worthy",
            "model": "flux-kontext-max",
            "upsampling": True,
        },
    }
    return presets


def main():
    """主界面"""
    init_session_state()

    # 标题
    st.markdown(
        '<h1 class="main-header">🎨 Flux Kontext AI图像编辑器</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #666;">基于文本指令的多图片AI融合编辑工具</p>',
        unsafe_allow_html=True,
    )

    # 侧边栏
    with st.sidebar:
        st.markdown("### 🛠️ 工具设置")

        # 配置检查
        create_config_section()

        st.markdown("---")

        # 质量预设
        st.markdown("### 🎯 质量预设")
        presets = quality_presets()
        selected_preset = st.selectbox("选择质量预设", list(presets.keys()))
        preset_config = presets[selected_preset]

        st.markdown("---")

        # 高级设置
        st.markdown("### ⚙️ 高级设置")

        # 模型选择
        model = st.selectbox(
            "AI模型",
            ["flux-kontext-pro", "flux-kontext-max"],
            index=0 if preset_config["model"] == "flux-kontext-pro" else 1,
            help="Pro模型更快，Max模型质量更高",
        )

        # 宽高比
        aspect_ratio = st.selectbox(
            "宽高比",
            ["1:1", "4:3", "3:4", "16:9", "9:16", "21:9", "9:21"],
            index=1,  # 默认4:3
            help="选择输出图像的宽高比",
        )

        # 安全等级
        safety_tolerance = st.slider(
            "安全等级",
            min_value=0,
            max_value=6,
            value=1,
            help="较低的安全等级允许更多创意，但可能产生不当内容",
        )

        # 输出格式
        output_format = st.selectbox(
            "输出格式", ["png", "jpeg"], help="PNG质量更高但文件更大，JPEG文件更小"
        )

        # 提示词增强
        prompt_upsampling = st.checkbox(
            "启用提示词增强",
            value=preset_config["upsampling"],
            help="AI会自动优化您的提示词以获得更好效果",
        )

        # 随机种子
        use_seed = st.checkbox("使用固定种子")
        seed = -1
        if use_seed:
            seed = st.number_input(
                "种子值", min_value=0, max_value=2147483647, value=42
            )

    # 主内容区域
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            '<h2 class="sub-header">📸 上传图片（可选）</h2>', unsafe_allow_html=True
        )

        # 图片上传
        uploaded_files = st.file_uploader(
            "选择要编辑的图片（可选，最多4张）",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="可选择上传JPG、JPEG、PNG格式图片进行编辑。如不上传，将进行纯文本生成",
        )

        if uploaded_files:
            if len(uploaded_files) > 4:
                st.warning("⚠️ 最多只能上传4张图片，将使用前4张")
                uploaded_files = uploaded_files[:4]

            st.success(f"✅ 已上传 {len(uploaded_files)} 张图片")

            # 显示上传的图片
            cols = st.columns(min(len(uploaded_files), 4))
            for i, uploaded_file in enumerate(uploaded_files):
                with cols[i]:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=f"图片 {i+1}", use_container_width=True)

    with col2:
        st.markdown(
            '<h2 class="sub-header">✏️ 生成/编辑指令</h2>', unsafe_allow_html=True
        )

        # 编辑指令输入
        edit_instruction = st.text_area(
            "描述您想要的图片效果",
            value=st.session_state.edit_instruction,
            height=100,
            placeholder="例如：Create a photo of exactly one person with one golden retriever dog, sitting together in a cozy living room",
            help="用自然语言描述您希望生成或编辑的图片效果。如果上传了图片，将进行编辑；否则将从头生成新图片",
            key="edit_instruction_input",
        )

        # 更新session state
        if edit_instruction != st.session_state.edit_instruction:
            st.session_state.edit_instruction = edit_instruction

        # 快速提示词模板
        st.markdown("#### 🚀 快速模板")

        # 显示当前模式
        has_images = uploaded_files and len(uploaded_files) > 0
        mode_text = "🖼️ 图片编辑模式" if has_images else "🎨 文本生成模式"
        st.info(f"当前模式: {mode_text}")

        template_cols = st.columns(2)

        with template_cols[0]:
            if st.button("👨‍👩‍👧‍👦 家庭合照"):
                if has_images:
                    st.session_state.edit_instruction = "Create a warm family portrait with all people sitting together in a cozy living room, natural lighting, professional photography"
                else:
                    st.session_state.edit_instruction = "Generate a warm family portrait of 4 people (parents and 2 children) sitting together in a cozy living room, natural lighting, professional photography, high quality"
                st.rerun()

            if st.button("🐕 人宠合影"):
                if has_images:
                    st.session_state.edit_instruction = "Create a photo of exactly one person with one golden retriever dog, sitting side by side in a living room, high quality portrait"
                else:
                    st.session_state.edit_instruction = "Generate a photo of exactly one person with one golden retriever dog, sitting side by side in a living room, high quality portrait, professional photography"
                st.rerun()

        with template_cols[1]:
            if st.button("🏞️ 风景照片"):
                if has_images:
                    st.session_state.edit_instruction = "Combine these landscapes into a beautiful panoramic view, natural lighting, scenic composition"
                else:
                    st.session_state.edit_instruction = "Generate a beautiful landscape panoramic view with mountains, lake, and trees, natural lighting, scenic composition, 4K quality"
                st.rerun()

            if st.button("🛍️ 产品展示"):
                if has_images:
                    st.session_state.edit_instruction = "Create a professional product showcase with all items on a modern display, white background, commercial photography"
                else:
                    st.session_state.edit_instruction = "Generate a professional product showcase of modern electronics on a clean white background, commercial photography, studio lighting, 4K quality"
                st.rerun()

        # 质量关键词添加
        st.markdown("#### ✨ 质量增强")
        if st.button("🎨 添加质量关键词"):
            quality_keywords = preset_config["keywords"]
            current_instruction = st.session_state.get("edit_instruction", "")
            if current_instruction:
                st.session_state.edit_instruction = (
                    f"{current_instruction}, {quality_keywords}"
                )
            else:
                st.session_state.edit_instruction = (
                    f"High quality photo, {quality_keywords}"
                )
            st.rerun()

    # 编辑按钮和结果
    st.markdown("---")

    col3, col4, col5 = st.columns([1, 2, 1])

    with col4:
        # 动态按钮文本
        button_text = (
            "🎨 开始AI编辑"
            if (uploaded_files and len(uploaded_files) > 0)
            else "🎨 开始AI生成"
        )

        if st.button(button_text, type="primary"):
            if not st.session_state.edit_instruction.strip():
                st.error("❌ 请输入生成/编辑指令")
            elif not st.session_state.api_key.strip():
                st.error("❌ 请先在侧边栏配置API密钥")
            else:
                # 检查编辑器
                if not load_editor():
                    return

                # 开始处理
                st.session_state.processing = True

                # 保存上传的文件（如果有的话）
                temp_paths = []
                if uploaded_files:
                    for i, uploaded_file in enumerate(uploaded_files):
                        temp_path = (
                            f"temp_image_{i}.{uploaded_file.name.split('.')[-1]}"
                        )
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        temp_paths.append(temp_path)

                # 清空之前的日志
                st.session_state.log_messages = []

                # 创建并排布局：左侧进度，右侧结果
                st.markdown("### 🔄 处理进度与结果")
                main_col1, main_col2 = st.columns([1, 1])

                # 左侧：进度显示
                with main_col1:
                    st.markdown("#### ⏳ 处理进度")

                    # 主进度条
                    progress_bar = st.progress(0)

                    # 状态显示
                    status_col1, status_col2 = st.columns([3, 1])
                    with status_col1:
                        status_text = st.empty()
                    with status_col2:
                        progress_percent = st.empty()

                    # 日志区域 - 创建固定的日志容器
                    st.markdown("#### 📋 处理日志")

                    # 日志内容占位符
                    log_content_placeholder = st.empty()

                # 右侧：结果预览
                with main_col2:
                    st.markdown("#### 🎊 结果预览")
                    result_placeholder = st.empty()
                    download_placeholder = st.empty()

                # 进度回调函数
                def update_progress(message, current, total):
                    """更新进度显示"""
                    progress = (
                        min(int((current / total) * 100), 100) if total > 0 else 0
                    )

                    # 更新进度条
                    progress_bar.progress(progress)

                    # 更新状态文本
                    status_text.markdown(f"**{message}**")
                    progress_percent.markdown(f"**{progress}%**")

                    # 添加到日志
                    timestamp = time.strftime("%H:%M:%S")
                    st.session_state.log_messages.append(f"[{timestamp}] {message}")

                    # 更新日志内容（只有在展开状态才显示）
                    if st.session_state.log_expanded:
                        # 显示最近的日志（限制显示条数以提高性能）
                        recent_logs = st.session_state.log_messages[
                            -15:
                        ]  # 只显示最近15条日志
                        log_text = "\n".join(recent_logs)

                        # HTML转义日志内容
                        import html

                        escaped_log_text = html.escape(log_text)

                        # 创建一个带滚动的日志容器
                        log_container_html = f"""
                        <div style="
                            height: 200px; 
                            overflow-y: auto; 
                            background-color: #1e1e1e; 
                            color: #ffffff; 
                            padding: 10px; 
                            border-radius: 5px; 
                            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
                            font-size: 0.85rem; 
                            line-height: 1.4; 
                            white-space: pre-wrap; 
                            border: 1px solid #404040;
                            ">{escaped_log_text}</div>
                        """

                        with log_content_placeholder:
                            st.markdown(log_container_html, unsafe_allow_html=True)
                    else:
                        # 折叠状态下清空内容
                        log_content_placeholder.empty()

                    # 强制刷新界面
                    time.sleep(0.1)

                try:
                    # 初始化进度
                    update_progress("🚀 开始处理...", 0, 100)

                    # 执行编辑
                    result = st.session_state.editor.edit_multi_images_native(
                        image_paths=temp_paths,
                        edit_instruction=st.session_state.edit_instruction,
                        output_path=f"flux_edited_{int(time.time())}.{output_format}",
                        model=model,
                        aspect_ratio=aspect_ratio,
                        output_format=output_format,
                        safety_tolerance=safety_tolerance,
                        seed=seed,
                        prompt_upsampling=prompt_upsampling,
                        progress_callback=update_progress,
                    )

                    if result:
                        update_progress("🎉 编辑完成！", 100, 100)
                        st.session_state.result_image = result

                        # 在右侧显示结果
                        with result_placeholder.container():
                            result_image = Image.open(result)
                            st.image(
                                result_image,
                                caption="生成/编辑后的图片",
                                use_container_width=True,
                            )

                        # 在右侧显示下载按钮
                        with download_placeholder.container():
                            download_label = (
                                "📥 下载编辑后的图片"
                                if (uploaded_files and len(uploaded_files) > 0)
                                else "📥 下载生成的图片"
                            )
                            with open(result, "rb") as file:
                                st.download_button(
                                    label=download_label,
                                    data=file.read(),
                                    file_name=f"flux_generated_{int(time.time())}.{output_format}",
                                    mime=f"image/{output_format}",
                                    key="download_progress_result",
                                )

                        # 显示成功消息
                        st.success("🎉 图片处理成功完成!")

                    else:
                        update_progress("❌ 编辑失败", 100, 100)
                        st.error("😞 图片编辑失败，请检查设置并重试")

                except Exception as e:
                    update_progress(f"❌ 处理出错: {str(e)}", 100, 100)
                    st.error(f"❌ 处理过程中出现错误: {str(e)}")

                finally:
                    # 清理临时文件
                    for temp_path in temp_paths:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                    # 清理临时配置文件
                    if os.path.exists("temp_config.ini"):
                        os.remove("temp_config.ini")

                    st.session_state.processing = False

    # 使用技巧
    with st.expander("💡 使用技巧和建议"):
        st.markdown(
            """
        ### 🎯 获得最佳效果的建议
        
        **🔄 工作模式:**
        - **图片编辑模式**: 上传图片进行AI编辑和融合
        - **文本生成模式**: 仅输入文字描述，从头生成全新图片
        
        **📸 提示词技巧:**
        - 使用具体、详细的描述
        - 指定确切的人数和物体数量
        - 添加质量关键词如 "professional photography", "4K resolution"
        - 描述光照和构图，如 "natural lighting", "perfect composition"
        - **文本生成时**: 更详细地描述场景、人物、环境和风格
        
        **⚙️ 参数建议:**
        - **高质量**: 选择Max模型 + 启用提示词增强
        - **快速处理**: 选择Pro模型 + 关闭提示词增强  
        - **避免多人**: 使用低安全等级(0-2) + 明确数量描述
        - **一致结果**: 使用固定种子
        
        **🎨 质量关键词:**
        - 基础: `high quality, clear, sharp`
        - 专业: `professional photography, studio quality`
        - 超高清: `4K resolution, 8K ultra HD, crystal clear`
        - 艺术: `masterpiece, fine art, museum quality`
        
        **💡 文本生成技巧:**
        - 详细描述人物外观、服装、表情
        - 明确指定场景环境和背景
        - 添加摄影风格和光照描述
        - 使用艺术风格关键词增强效果
        
        **⚠️ 常见问题:**
        - 如果出现多余人物，降低安全等级并使用更明确的提示词
        - 如果质量不够，选择Max模型并添加质量关键词
        - 如果处理失败，检查API密钥和网络连接
        - 文本生成时要更详细描述，避免模糊表达
        """
        )

    # 底部信息
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🎨 Powered by Flux Kontext API | 
        <a href="https://api.bfl.ai" target="_blank">获取API密钥</a> | 
        Made with ❤️ using Streamlit
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
