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
    if "api_configured" not in st.session_state:
        st.session_state.api_configured = False


def load_editor():
    """加载编辑器"""
    try:
        if st.session_state.editor is None:
            # 使用页面配置的API密钥
            if st.session_state.api_key.strip():
                # 临时创建配置文件
                config_content = f"""[API]
X_KEY = {st.session_state.api_key.strip()}
BASE_URL = https://api.bfl.ai
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

    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        st.session_state.editor = None  # 重置编辑器以使用新密钥
        st.session_state.api_configured = False

    if st.session_state.api_key.strip():
        st.success("✅ API密钥已配置")
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
        st.markdown('<h2 class="sub-header">📸 上传图片</h2>', unsafe_allow_html=True)

        # 图片上传
        uploaded_files = st.file_uploader(
            "选择要编辑的图片（最多4张）",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="支持JPG、JPEG、PNG格式，最多同时处理4张图片",
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
                    st.image(image, caption=f"图片 {i+1}", use_container_width =True)

    with col2:
        st.markdown('<h2 class="sub-header">✏️ 编辑指令</h2>', unsafe_allow_html=True)

        # 编辑指令输入
        edit_instruction = st.text_area(
            "描述您想要的编辑效果",
            value=st.session_state.edit_instruction,
            height=100,
            placeholder="例如：Create a photo of exactly one person with one golden retriever dog, sitting together in a cozy living room",
            help="用自然语言描述您希望如何编辑图片",
            key="edit_instruction_input",
        )

        # 更新session state
        if edit_instruction != st.session_state.edit_instruction:
            st.session_state.edit_instruction = edit_instruction

        # 快速提示词模板
        st.markdown("#### 🚀 快速模板")
        template_cols = st.columns(2)

        with template_cols[0]:
            if st.button("👨‍👩‍👧‍👦 家庭合照"):
                st.session_state.edit_instruction = "Create a warm family portrait with all people sitting together in a cozy living room, natural lighting, professional photography"
                st.rerun()

            if st.button("🐕 人宠合影"):
                st.session_state.edit_instruction = "Create a photo of exactly one person with one golden retriever dog, sitting side by side in a living room, high quality portrait"
                st.rerun()

        with template_cols[1]:
            if st.button("🏞️ 风景融合"):
                st.session_state.edit_instruction = "Combine these landscapes into a beautiful panoramic view, natural lighting, scenic composition"
                st.rerun()

            if st.button("🛍️ 产品展示"):
                st.session_state.edit_instruction = "Create a professional product showcase with all items on a modern display, white background, commercial photography"
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
        if st.button("🎨 开始AI编辑", type="primary"):
            if not uploaded_files:
                st.error("❌ 请先上传图片")
            elif not st.session_state.edit_instruction.strip():
                st.error("❌ 请输入编辑指令")
            elif not st.session_state.api_key.strip():
                st.error("❌ 请先在侧边栏配置API密钥")
            else:
                # 检查编辑器
                if not load_editor():
                    return

                # 开始处理
                st.session_state.processing = True

                # 保存上传的文件
                temp_paths = []
                for i, uploaded_file in enumerate(uploaded_files):
                    temp_path = f"temp_image_{i}.{uploaded_file.name.split('.')[-1]}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    temp_paths.append(temp_path)

                # 创建进度显示区域
                progress_container = st.container()
                with progress_container:
                    st.markdown("### 🔄 处理进度")

                    # 主进度条
                    progress_bar = st.progress(0)

                    # 状态显示
                    status_col1, status_col2 = st.columns([3, 1])
                    with status_col1:
                        status_text = st.empty()
                    with status_col2:
                        progress_percent = st.empty()

                    # 详细日志区域
                    st.markdown("#### 📋 处理日志")
                    log_container = st.container()
                    log_messages = []

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
                    log_messages.append(f"[{timestamp}] {message}")

                    # 显示最近的日志（最多显示8条）
                    recent_logs = log_messages[-8:]
                    log_text = "\n".join(recent_logs)

                    with log_container:
                        st.code(log_text, language=None)

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

                        # 显示成功消息
                        st.success("🎉 图片编辑成功完成!")

                        # 清除进度显示
                        time.sleep(2)
                        progress_container.empty()

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

    # 显示结果
    if st.session_state.result_image and os.path.exists(st.session_state.result_image):
        st.markdown("---")
        st.markdown('<h2 class="sub-header">🎊 编辑结果</h2>', unsafe_allow_html=True)

        col6, col7, col8 = st.columns([1, 2, 1])

        with col7:
            result_image = Image.open(st.session_state.result_image)
            st.image(result_image, caption="编辑后的图片", use_container_width =True)

            # 下载按钮
            with open(st.session_state.result_image, "rb") as file:
                st.download_button(
                    label="📥 下载编辑后的图片",
                    data=file.read(),
                    file_name=f"flux_edited_{int(time.time())}.{output_format}",
                    mime=f"image/{output_format}",
                )

    # 使用技巧
    with st.expander("💡 使用技巧和建议"):
        st.markdown(
            """
        ### 🎯 获得最佳效果的建议
        
        **📸 提示词技巧:**
        - 使用具体、详细的描述
        - 指定确切的人数和物体数量
        - 添加质量关键词如 "professional photography", "4K resolution"
        - 描述光照和构图，如 "natural lighting", "perfect composition"
        
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
        
        **⚠️ 常见问题:**
        - 如果出现多余人物，降低安全等级并使用更明确的提示词
        - 如果质量不够，选择Max模型并添加质量关键词
        - 如果处理失败，检查API密钥和网络连接
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
