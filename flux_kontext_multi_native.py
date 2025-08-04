"""
Flux Kontext 原生多图片编辑器
使用 BFL API 的原生多图片支持功能
直接发送多张图片到API，让AI进行融合处理

使用方法:
python flux_kontext_multi_native.py --inputs image1.jpg image2.jpg image3.jpg --prompt "将这些人物融合成一张全家福" --output result.png

依赖安装:
pip install requests pillow numpy
"""

import requests
from PIL import Image
import io
import numpy as np
import os
import configparser
import time
import base64
import argparse
from enum import Enum
from pathlib import Path


class Status(Enum):
    PENDING = "Pending"
    READY = "Ready"
    ERROR = "Error"


class ConfigLoader:
    """配置加载器 - 从config.ini读取API配置"""

    def __init__(self, config_path=None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "config.ini")

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"配置文件未找到: {config_path}\n请创建config.ini文件并添加您的API密钥"
            )

        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding="utf-8")
        self.set_api_config()

    def set_api_config(self):
        """设置API配置"""
        try:
            if not self.config.has_section("API"):
                raise KeyError("配置文件中未找到 [API] 部分")

            # 设置 X_KEY
            if not self.config.has_option("API", "X_KEY"):
                raise KeyError("配置文件中未找到 X_KEY")
            x_key = self.config["API"]["X_KEY"]
            if not x_key:
                raise KeyError("X_KEY 不能为空")
            os.environ["X_KEY"] = x_key

            # 设置 BASE_URL
            if self.config.has_option("API", "BASE_URL"):
                base_url = self.config["API"]["BASE_URL"]
                if base_url == "https://api.bfl.ml":
                    print("⚠️  警告: api.bfl.ml 是文档站点，使用 api.bfl.ai 进行API调用")
                    base_url = "https://api.bfl.ai"
                elif not base_url.startswith("http"):
                    base_url = f"https://{base_url}"
            else:
                base_url = "https://api.bfl.ai"

            os.environ["BASE_URL"] = base_url
            print(f"🔗 API端点: {base_url}")

        except KeyError as e:
            print(f"❌ 配置错误: {str(e)}")
            print("请确保config.ini包含以下格式:")
            print("[API]")
            print("X_KEY = 您的API密钥")
            print("BASE_URL = https://api.bfl.ai")
            raise


class FluxKontextNativeMultiEditor:
    """Flux Kontext 原生多图片编辑器"""

    def __init__(self, config_path=None):
        """初始化编辑器"""
        try:
            self.config_loader = ConfigLoader(config_path)
            print("✅ Flux Kontext 原生多图片编辑器初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {str(e)}")
            raise

    def edit_multi_images_native(
        self,
        image_paths,
        edit_instruction,
        output_path=None,
        model="flux-kontext-pro",
        aspect_ratio="1:1",
        output_format="png",
        safety_tolerance=2,  # 降低安全等级，减少过度保守的生成
        seed=-1,  # 使用随机种子，避免固定模式
        prompt_upsampling=False,
        progress_callback=None,
    ):
        """
        使用API原生多图片支持进行编辑

        参数:
            image_paths: 输入图像路径列表 (最多4张)
            edit_instruction: 编辑指令文本
            output_path: 输出图像路径 (可选)
            model: 模型选择 ("flux-kontext-pro" 或 "flux-kontext-max")
            aspect_ratio: 宽高比
            output_format: 输出格式 ("png" 或 "jpeg")
            safety_tolerance: 安全等级 (0-6)
            seed: 随机种子 (-1为随机)
            prompt_upsampling: 是否启用提示词增强
            progress_callback: 进度回调函数

        返回:
            成功时返回输出路径，失败时返回None
        """
        print(f"🎨 开始原生多图片编辑")
        print(f"📝 编辑指令: {edit_instruction}")
        print(f"🤖 使用模型: {model}")
        print(f"📊 输入图片数量: {len(image_paths)}")

        if progress_callback:
            progress_callback("🎨 开始处理图片...", 0, 100)

        # 验证输入
        if not edit_instruction.strip():
            print("❌ 编辑指令不能为空")
            if progress_callback:
                progress_callback("❌ 编辑指令不能为空", 0, 100)
            return None

        if not image_paths:
            print("❌ 没有提供输入图片")
            if progress_callback:
                progress_callback("❌ 没有提供输入图片", 0, 100)
            return None

        if len(image_paths) > 4:
            print("⚠️  API最多支持4张图片，将使用前4张")
            if progress_callback:
                progress_callback("⚠️ API最多支持4张图片，将使用前4张", 10, 100)
            image_paths = image_paths[:4]

        try:
            # 将图片转换为base64
            if progress_callback:
                progress_callback("🔄 正在处理图片...", 20, 100)

            base64_images = []
            for i, path in enumerate(image_paths):
                if not os.path.exists(path):
                    print(f"❌ 图片文件不存在: {path}")
                    if progress_callback:
                        progress_callback(f"❌ 图片文件不存在: {path}", 20, 100)
                    return None

                try:
                    image = Image.open(path)
                    if image.mode != "RGB":
                        image = image.convert("RGB")

                    # 调整图片大小以符合API要求
                    max_size = 2048
                    if max(image.size) > max_size:
                        ratio = max_size / max(image.size)
                        new_size = (int(image.width * ratio), int(image.height * ratio))
                        image = image.resize(new_size, Image.Resampling.LANCZOS)
                        print(f"📏 图片 {i+1} 已调整大小: {new_size}")

                    base64_str = self.pil_to_base64(image)
                    if not base64_str:
                        print(f"❌ 图片 {i+1} 编码失败")
                        if progress_callback:
                            progress_callback(f"❌ 图片 {i+1} 编码失败", 20, 100)
                        return None

                    base64_images.append(base64_str)
                    print(f"✅ 图片 {i+1} 处理完成")
                    if progress_callback:
                        progress_callback(
                            f"✅ 图片 {i+1} 处理完成", 20 + (i + 1) * 10, 100
                        )

                except Exception as e:
                    print(f"❌ 处理图片 {i+1} 时出错: {str(e)}")
                    if progress_callback:
                        progress_callback(
                            f"❌ 处理图片 {i+1} 时出错: {str(e)}", 20, 100
                        )
                    return None

            # 构建API请求
            if progress_callback:
                progress_callback("🚀 正在发送请求到AI服务器...", 60, 100)

            base_url = os.environ.get("BASE_URL", "https://api.bfl.ai")
            url = f"{base_url}/v1/flux-kontext-pro"

            payload = {
                "prompt": edit_instruction,
                "input_image": base64_images[0],  # 主要图片
                "aspect_ratio": aspect_ratio,
                "safety_tolerance": safety_tolerance,
                "output_format": output_format,
                "prompt_upsampling": prompt_upsampling,
            }

            # 添加额外的图片
            if len(base64_images) > 1:
                payload["input_image_2"] = base64_images[1]
            if len(base64_images) > 2:
                payload["input_image_3"] = base64_images[2]
            if len(base64_images) > 3:
                payload["input_image_4"] = base64_images[3]

            if seed >= 0:
                payload["seed"] = seed

            # 发送请求
            x_key = os.environ.get("X_KEY")
            if not x_key:
                print("❌ API密钥未找到，请检查config.ini")
                if progress_callback:
                    progress_callback("❌ API密钥未找到", 60, 100)
                return None

            headers = {"x-key": x_key, "Content-Type": "application/json"}

            # 发送请求
            print(f"🚀 发送原生多图片请求到: {url}")
            print(
                f"📊 请求包含 {len([k for k in payload.keys() if k.startswith('input_image')])} 张图片"
            )

            response = requests.post(url, json=payload, headers=headers, timeout=60)
            print(f"📡 响应状态: {response.status_code}")

            # 处理响应
            if response.status_code == 200:
                response_data = response.json()
                task_id = response_data.get("id")

                if not task_id:
                    print("❌ 未收到任务ID")
                    print(f"响应内容: {response_data}")
                    if progress_callback:
                        progress_callback("❌ 未收到任务ID", 60, 100)
                    return None

                print(f"🆔 任务ID: {task_id}")
                if progress_callback:
                    progress_callback(f"✅ 任务已提交 (ID: {task_id[:8]}...)", 70, 100)

                # 等待结果
                result_image = self.wait_for_result(
                    task_id, progress_callback=progress_callback
                )

                if result_image is not None:
                    # 保存结果
                    if output_path is None:
                        # 自动生成输出路径
                        output_path = (
                            f"native_multi_edited_{int(time.time())}.{output_format}"
                        )

                    result_image.save(output_path, format=output_format.upper())
                    print(f"✅ 原生多图片编辑完成! 保存到: {output_path}")
                    if progress_callback:
                        progress_callback("🎉 图片编辑完成！", 100, 100)
                    return output_path
                else:
                    print("❌ 图像生成失败")
                    if progress_callback:
                        progress_callback("❌ 图像生成失败", 100, 100)
                    return None

            elif response.status_code == 400:
                print(f"❌ 请求参数错误: {response.text}")
                if progress_callback:
                    progress_callback(f"❌ 请求参数错误: {response.text}", 60, 100)
                return None
            elif response.status_code == 401:
                print("❌ API密钥无效，请检查config.ini中的X_KEY")
                if progress_callback:
                    progress_callback("❌ API密钥无效", 60, 100)
                return None
            else:
                print(f"❌ 请求失败: {response.status_code} - {response.text}")
                if progress_callback:
                    progress_callback(f"❌ 请求失败: {response.status_code}", 60, 100)
                return None

        except requests.exceptions.Timeout:
            print("❌ 请求超时，请重试")
            if progress_callback:
                progress_callback("❌ 请求超时，请重试", 60, 100)
            return None
        except requests.exceptions.ConnectionError:
            print("❌ 网络连接错误，请检查网络")
            if progress_callback:
                progress_callback("❌ 网络连接错误", 60, 100)
            return None
        except Exception as e:
            print(f"❌ 意外错误: {str(e)}")
            if progress_callback:
                progress_callback(f"❌ 意外错误: {str(e)}", 60, 100)
            return None

    def pil_to_base64(self, pil_image):
        """将PIL图像转换为base64字符串"""
        try:
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            print(f"🔄 图像已编码: {len(img_base64)} 字符")
            return img_base64
        except Exception as e:
            print(f"❌ 图像编码错误: {str(e)}")
            return None

    def wait_for_result(self, task_id, max_attempts=30, progress_callback=None):
        """等待API处理结果"""
        print(f"⏳ 等待处理结果: {task_id}")
        base_url = os.environ.get("BASE_URL", "https://api.bfl.ai")

        if progress_callback:
            progress_callback("🚀 任务已提交，开始处理...", 0, max_attempts)

        for attempt in range(1, max_attempts + 1):
            try:
                # 渐进式等待时间 - 多图片处理可能需要更长时间
                wait_time = min(3 + attempt, 20)

                if progress_callback:
                    progress_callback(
                        f"🔄 检查进度 {attempt}/{max_attempts} - 等待 {wait_time}秒",
                        attempt,
                        max_attempts,
                    )

                print(f"🔄 尝试 {attempt}/{max_attempts} - 等待 {wait_time}秒")
                time.sleep(wait_time)

                # 检查任务状态
                get_url = f"{base_url}/v1/get_result?id={task_id}"
                headers = {"x-key": os.environ["X_KEY"]}
                print(f"🔄 检查任务状态: {get_url}")

                response = requests.get(get_url, headers=headers, timeout=30)

                if response.status_code != 200:
                    print(f"⚠️  状态检查失败: {response.status_code}")
                    if progress_callback:
                        progress_callback(
                            f"⚠️ 状态检查失败，重试中... ({response.status_code})",
                            attempt,
                            max_attempts,
                        )
                    continue

                result = response.json()
                status = result.get("status", "Unknown")
                print(f"📊 状态: {status}")

                if status == Status.READY.value:
                    # 图像已准备好
                    if progress_callback:
                        progress_callback(
                            "✅ 图像生成完成，正在下载...", max_attempts, max_attempts
                        )

                    sample_url = result.get("result", {}).get("sample")
                    if not sample_url:
                        print("❌ 响应中没有图像URL")
                        if progress_callback:
                            progress_callback(
                                "❌ 响应中没有图像URL", attempt, max_attempts
                            )
                        return None

                    # 下载图像
                    print(f"⬇️  下载图像: {sample_url}")
                    if progress_callback:
                        progress_callback(
                            "⬇️ 正在下载生成的图像...", max_attempts, max_attempts
                        )

                    img_response = requests.get(sample_url, timeout=30)

                    if img_response.status_code == 200:
                        image = Image.open(io.BytesIO(img_response.content))
                        print("✅ 图像下载成功")
                        if progress_callback:
                            progress_callback(
                                "🎉 图像处理完成！", max_attempts, max_attempts
                            )
                        return image
                    else:
                        print(f"❌ 图像下载失败: {img_response.status_code}")
                        if progress_callback:
                            progress_callback(
                                f"❌ 图像下载失败: {img_response.status_code}",
                                attempt,
                                max_attempts,
                            )
                        return None

                elif status == Status.ERROR.value:
                    error_msg = result.get("error", "未知错误")
                    print(f"❌ 处理失败: {error_msg}")
                    if progress_callback:
                        progress_callback(
                            f"❌ 处理失败: {error_msg}", attempt, max_attempts
                        )
                    return None

                elif status == Status.PENDING.value:
                    if progress_callback:
                        progress_callback(
                            f"⏳ 正在处理中... ({attempt}/{max_attempts})",
                            attempt,
                            max_attempts,
                        )
                    print("⏳ 仍在处理中...")
                else:
                    if progress_callback:
                        progress_callback(
                            f"📊 状态: {status} ({attempt}/{max_attempts})",
                            attempt,
                            max_attempts,
                        )
                    print(f"📊 未知状态: {status}")

            except requests.exceptions.Timeout:
                print(f"⏰ 请求超时 (尝试 {attempt}/{max_attempts})")
                if progress_callback:
                    progress_callback(
                        f"⏰ 请求超时，重试中... ({attempt}/{max_attempts})",
                        attempt,
                        max_attempts,
                    )
                continue
            except requests.exceptions.ConnectionError:
                print(f"🌐 网络连接错误 (尝试 {attempt}/{max_attempts})")
                if progress_callback:
                    progress_callback(
                        f"🌐 网络连接错误，重试中... ({attempt}/{max_attempts})",
                        attempt,
                        max_attempts,
                    )
                continue
            except Exception as e:
                print(f"❌ 意外错误: {str(e)}")
                if progress_callback:
                    progress_callback(f"❌ 意外错误: {str(e)}", attempt, max_attempts)
                continue

        print("❌ 达到最大尝试次数，处理失败")
        if progress_callback:
            progress_callback("❌ 处理超时，请重试", max_attempts, max_attempts)
        return None


def create_sample_config():
    """创建示例配置文件"""
    config_content = """[API]
# 从 https://api.bfl.ai 获取您的API密钥
X_KEY = 在此输入您的API密钥
BASE_URL = https://api.bfl.ai
"""

    with open("config.ini", "w", encoding="utf-8") as f:
        f.write(config_content)

    print("📝 已创建示例配置文件 config.ini")
    print("请编辑此文件并添加您的API密钥")


def main():
    """主函数 - 命令行界面"""
    parser = argparse.ArgumentParser(description="Flux Kontext 原生多图片编辑工具")
    parser.add_argument(
        "--inputs", "-i", nargs="+", required=True, help="输入图像路径列表 (最多4张)"
    )
    parser.add_argument("--prompt", "-p", required=True, help="编辑指令")
    parser.add_argument("--output", "-o", help="输出图像路径 (可选)")
    parser.add_argument(
        "--model",
        "-m",
        choices=["flux-kontext-pro", "flux-kontext-max"],
        default="flux-kontext-pro",
        help="选择模型",
    )
    parser.add_argument(
        "--aspect-ratio",
        "-ar",
        choices=["1:1", "4:3", "3:4", "16:9", "9:16", "21:9", "9:21"],
        default="1:1",
        help="宽高比",
    )
    parser.add_argument(
        "--format", "-f", choices=["png", "jpeg"], default="png", help="输出格式"
    )
    parser.add_argument(
        "--safety",
        "-s",
        type=int,
        choices=range(0, 7),
        default=4,
        help="安全等级 (0-6)",
    )
    parser.add_argument("--seed", type=int, default=-1, help="随机种子 (-1为随机)")
    parser.add_argument(
        "--prompt-upsampling", action="store_true", help="启用提示词增强"
    )
    parser.add_argument("--create-config", action="store_true", help="创建示例配置文件")

    args = parser.parse_args()

    # 创建配置文件
    if args.create_config:
        create_sample_config()
        return

    try:
        # 初始化编辑器
        editor = FluxKontextNativeMultiEditor()

        # 执行原生多图片编辑
        result = editor.edit_multi_images_native(
            image_paths=args.inputs,
            edit_instruction=args.prompt,
            output_path=args.output,
            model=args.model,
            aspect_ratio=args.aspect_ratio,
            output_format=args.format,
            safety_tolerance=args.safety,
            seed=args.seed,
            prompt_upsampling=args.prompt_upsampling,
        )

        if result:
            print(f"🎉 原生多图片编辑成功完成: {result}")
        else:
            print("😞 编辑失败")
            exit(1)

    except FileNotFoundError as e:
        print(f"❌ {str(e)}")
        print("\n💡 提示: 使用 --create-config 创建配置文件模板")
        exit(1)
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        exit(1)


if __name__ == "__main__":
    print("🎨 Flux Kontext 原生多图片编辑器")
    print("=" * 50)
    main()
