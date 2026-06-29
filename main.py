"""
BIMBase 自然语言建模工具 — CLI 主入口
"""
import os
import sys
import logging
import datetime

from config import OUTPUT_DIR, LLM_MAX_VALIDATION_RETRIES, ENABLE_CLARIFICATION
from llm_client import LLMClient
from system_prompt import build_system_prompt
from code_validator import validate_code, extract_code, build_fix_prompt
from param_extractor import extract_params, build_augmented_spec

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bimbase_nl")


def clarify_requirements(client: LLMClient, user_input: str) -> str:
    """
    需求澄清环节（P0）：抽取参数，对模糊输入反问缺失项。
    返回给生成阶段使用的（可能增强后的）需求描述。

    - 抽取失败或输入已完整 → 原样返回 user_input
    - 有 critical 缺失 → 展示带默认值，用户可选 Y/n/s
    """
    if not ENABLE_CLARIFICATION:
        return user_input

    print("\n[分析需求...]")
    extraction = extract_params(client, user_input)

    # 抽取失败或无需澄清 → 直接生成
    if not extraction.parse_ok or not extraction.needs_clarification:
        if extraction.parse_ok and extraction.building_type:
            print(f"  推断建筑类型: {extraction.building_type}")
            if extraction.provided:
                print("  已提供参数:")
                for k, v in extraction.provided.items():
                    print(f"    - {k}: {v}")
            print("  参数完整，直接生成。")
        return user_input

    # 展示抽取结果
    print(f"  推断建筑类型: {extraction.building_type}")
    if extraction.provided:
        print("  已提供参数:")
        for k, v in extraction.provided.items():
            print(f"    - {k}: {v}")
    print("  缺少关键参数(已附默认建议):")
    for i, mp in enumerate(extraction.critical_missing, 1):
        print(f"    {i}. {mp.key} — 默认: {mp.default}{mp.unit}"
              + (f"  ({mp.reason})" if mp.reason else ""))

    # 询问用户
    choice = input("\n  [Y]使用默认值 / [n]自己填写 / [s]跳过澄清直接生成 > ").strip().lower()

    if choice == "s":
        return user_input

    resolved = {}
    if choice == "n":
        for mp in extraction.critical_missing:
            val = input(f"    {mp.question} (默认 {mp.default}{mp.unit}): ").strip()
            resolved[mp.key] = val if val else mp.default
    else:
        # Y 或空回车 → 使用默认值
        resolved = {mp.key: mp.default for mp in extraction.critical_missing}

    return build_augmented_spec(user_input, extraction, resolved)


def generate_script(client: LLMClient, system_prompt: str, user_input: str) -> tuple:
    """
    生成 pyp3d 脚本，包含验证和自动修正。

    Returns:
        (code, validation_result) 元组
    """
    # 第一次生成
    logger.info("正在调用 DeepSeek API 生成代码...")
    raw_response = client.generate(system_prompt=system_prompt, user_message=user_input)

    # 提取代码
    code = extract_code(raw_response)

    # 验证
    result = validate_code(code)

    if result.passed:
        logger.info("代码验证通过")
        return code, result

    # 验证失败，尝试自我修正
    logger.warning(f"代码验证失败，尝试自我修正 (最多 {LLM_MAX_VALIDATION_RETRIES} 轮)...")

    messages = [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": raw_response},
    ]

    for retry in range(1, LLM_MAX_VALIDATION_RETRIES + 1):
        logger.info(f"自我修正第 {retry}/{LLM_MAX_VALIDATION_RETRIES} 轮...")

        fix_prompt = build_fix_prompt(code, result)
        messages.append({"role": "user", "content": fix_prompt})

        raw_response = client.generate_with_history(
            system_prompt=system_prompt,
            messages=messages,
        )

        code = extract_code(raw_response)
        result = validate_code(code)

        if result.passed:
            logger.info(f"第 {retry} 轮修正后验证通过")
            return code, result

        # 追加 assistant 回复到历史
        messages.append({"role": "assistant", "content": raw_response})

    logger.warning(f"经过 {LLM_MAX_VALIDATION_RETRIES} 轮修正仍未通过验证")
    return code, result


def save_script(code: str, description: str = "") -> str:
    """
    保存生成的脚本到 output/ 目录。

    Args:
        code: 脚本内容
        description: 简短描述（用于文件名）

    Returns:
        保存的文件路径
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 从描述中提取关键词作为文件名
    slug = ""
    if description:
        # 简单提取：取前几个字符，去除特殊字符
        slug = "".join(c for c in description[:20] if c.isalnum() or c in "_ ")
        slug = slug.strip().replace(" ", "_")
        if slug:
            slug = f"_{slug}"

    filename = f"script_{timestamp}{slug}.py"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    return filepath


def print_banner():
    """打印欢迎横幅。"""
    print()
    print("=" * 60)
    print("  BIMBase 自然语言建模工具")
    print("  输入中文描述 → 自动生成 pyp3d 脚本")
    print("=" * 60)
    print()
    print("命令:")
    print("  输入建筑描述  — 生成 pyp3d 脚本")
    print("  quit / exit   — 退出")
    print("  help          — 显示帮助信息")
    print()


def print_help():
    """打印帮助信息。"""
    print()
    print("帮助信息:")
    print("-" * 40)
    print("用中文描述你想要的建筑构件，例如:")
    print('  - 建一堵长6米厚0.3米高3米的墙')
    print('  - 创建一根圆柱柱子，半径300mm，高4米')
    print('  - 建一个三层框架，跨度6米，层高3米')
    print('  - 在墙上开一个1.5m宽2m高的门洞')
    print('  - 创建一个L型建筑，两翼各6米')
    print('  - 建一个12级的楼梯，踏步宽300高150')
    print()
    print("生成的脚本保存在:", OUTPUT_DIR)
    print("可在 BIMBase 建模软件 2025 中加载运行")
    print()


def run_interactive():
    """交互式主循环。"""
    print_banner()

    # 初始化
    try:
        client = LLMClient()
    except ValueError as e:
        print(f"[错误] {e}")
        print("请将密钥写入同目录下的 apikey.txt（或设置环境变量 DEEPSEEK_API_KEY）后再运行。")
        sys.exit(1)

    system_prompt = build_system_prompt()
    logger.info(f"系统 prompt 构建完成 ({len(system_prompt)} 字符)")

    while True:
        try:
            user_input = input("请输入建模描述 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if user_input.lower() == "help":
            print_help()
            continue

        # 生成脚本
        print()
        print("[正在生成...]")
        print()

        try:
            # P0: 需求澄清（对模糊输入反问缺失项）
            gen_input = clarify_requirements(client, user_input)

            code, validation = generate_script(client, system_prompt, gen_input)
        except RuntimeError as e:
            print(f"[错误] {e}")
            print()
            continue
        except Exception as e:
            print(f"[意外错误] {e}")
            logger.exception("生成过程出错")
            print()
            continue

        # 显示结果
        if validation.passed:
            print("✓ 代码验证通过")
        else:
            print("⚠ 代码验证未完全通过:")
            print(str(validation))

        # 保存
        filepath = save_script(code, user_input)
        print(f"✓ 已保存脚本: {filepath}")

        # 显示代码预览
        print()
        print("-" * 40)
        # 显示代码（限制行数）
        code_lines = code.split("\n")
        preview_lines = min(len(code_lines), 40)
        print("\n".join(code_lines[:preview_lines]))
        if len(code_lines) > preview_lines:
            print(f"... (共 {len(code_lines)} 行，已省略 {len(code_lines) - preview_lines} 行)")
        print("-" * 40)

        print()
        print(f"请在 BIMBase 中加载 {filepath} 运行")
        print()


if __name__ == "__main__":
    run_interactive()
