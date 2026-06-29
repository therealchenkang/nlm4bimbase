"""
BIMBase 自然语言建模工具 — 配置文件
"""
import os


def _load_deepseek_api_key() -> str:
    """
    读取 DeepSeek API Key。

    优先级：
      1. 环境变量 ``DEEPSEEK_API_KEY``（便于在服务器 / CI 上覆盖）；
      2. 同目录下的 ``apikey.txt``（本地开发默认方式；
         该文件已在 .gitignore 中，不会随仓库上传）。

    两者都未提供时返回空字符串，交由 LLMClient 在初始化时给出明确报错。
    """
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key

    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apikey.txt")
    if os.path.isfile(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    return ""


# ============ DeepSeek API 配置 ============
DEEPSEEK_API_KEY = _load_deepseek_api_key()
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"

# ============ LLM 参数 ============
LLM_TEMPERATURE = 0.0        # 代码生成用 0 确保确定性
LLM_TIMEOUT = 180            # 思考模型可能较慢，180s
LLM_MAX_RETRIES = 3          # 最大重试次数
LLM_MAX_VALIDATION_RETRIES = 3  # 验证失败后 LLM 自我修正的最大轮数

# ============ 需求澄清（P0）============
# 生成代码前先用一轮 LLM 抽取参数，对模糊输入主动反问缺失项。
# 关闭后回退为"单轮直出"旧行为。
ENABLE_CLARIFICATION = True
# 抽取参数是否启用思考模式（关闭可加速澄清响应）
EXTRACTION_USE_THINKING = False

# ============ 路径配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
REFERENCE_DIR = os.path.join(BASE_DIR, "reference")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
