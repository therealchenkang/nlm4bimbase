"""
代码验证器 — 三层验证：语法、导入、模式
"""
import ast
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果。"""
    passed: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def add_error(self, msg: str):
        self.passed = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def __str__(self):
        lines = []
        if self.passed:
            lines.append("验证通过")
        else:
            lines.append(f"验证失败 ({len(self.errors)} 个错误)")
        for e in self.errors:
            lines.append(f"  [ERROR] {e}")
        for w in self.warnings:
            lines.append(f"  [WARN]  {w}")
        return "\n".join(lines)


def validate_code(code: str) -> ValidationResult:
    """
    三层验证生成的 pyp3d 代码。

    1. 语法检查: ast.parse() 确认是合法 Python
    2. 导入检查: 确认有 from pyp3d import *，无非法导入
    3. 模式检查: 确认有 create_geometry 或 place 调用

    Args:
        code: 生成的 Python 代码字符串

    Returns:
        ValidationResult 验证结果对象
    """
    result = ValidationResult()

    # 预处理：去除 markdown 代码块标记
    code = _strip_markdown(code)

    # Layer 1: 语法检查
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result.add_error(f"语法错误 (line {e.lineno}): {e.msg}")
        return result  # 语法错误时直接返回，后续检查无法进行

    # Layer 2: 导入检查
    _check_imports(tree, code, result)

    # Layer 3: 模式检查
    _check_patterns(tree, code, result)

    return result


def extract_code(raw_response: str) -> str:
    """
    从 LLM 响应中提取纯代码。
    处理可能包含的 markdown 代码块标记和多余文字。
    """
    code = raw_response.strip()

    # 去除 markdown 代码块
    code = _strip_markdown(code)

    # 如果响应包含非代码文本，尝试提取代码部分
    # 查找 "from pyp3d import *" 开始的位置
    idx = code.find("from pyp3d import *")
    if idx > 0:
        # 检查前面是否有非代码内容
        prefix = code[:idx].strip()
        if prefix and not prefix.startswith("#"):
            code = code[idx:]

    return code.strip()


def _strip_markdown(code: str) -> str:
    """去除 markdown 代码块标记。"""
    # 匹配 ```python ... ``` 或 ``` ... ```
    pattern = r"```(?:python)?\s*\n(.*?)\n```"
    match = re.search(pattern, code, re.DOTALL)
    if match:
        return match.group(1).strip()
    return code.strip()


def _check_imports(tree: ast.AST, code: str, result: ValidationResult):
    """检查导入语句。"""
    has_pyp3d_import = False
    illegal_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "pyp3d":
                    has_pyp3d_import = True
                else:
                    illegal_imports.append(f"import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyp3d":
                has_pyp3d_import = True
            elif module and module not in ("math",):
                # 允许 math 模块，其他外部库不允许
                illegal_imports.append(f"from {module} import ...")

    if not has_pyp3d_import:
        # 也在原始代码中检查
        if "from pyp3d import *" in code:
            has_pyp3d_import = True

    if not has_pyp3d_import:
        result.add_error("缺少必要的导入: 'from pyp3d import *'")

    if illegal_imports:
        for imp in illegal_imports:
            result.add_error(f"不允许的导入: {imp} (pyp3d 脚本只能使用 pyp3d 和标准库)")


def _check_patterns(tree: ast.AST, code: str, result: ValidationResult):
    """检查代码是否包含必要的模式。"""
    has_create_geometry = False
    has_place = False
    has_geometry_op = False

    # 检查函数调用
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = _get_func_name(node)
            if func_name == "create_geometry":
                has_create_geometry = True
            elif func_name == "place":
                has_place = True
            elif func_name in (
                "Cube", "Sphere", "Cone",
                "Box", "Section", "Arc", "Line",
                "Loft", "Sweep", "Extrusion", "Combine",
                "Fusion", "Intersect",
            ):
                has_geometry_op = True

    if not has_create_geometry and not has_place:
        result.add_error(
            "代码缺少 create_geometry() 或 place() 调用。"
            "生成的几何体需要通过 create_geometry() 创建才能在 BIMBase 中显示。"
        )

    if not has_geometry_op and not has_create_geometry and not has_place:
        result.add_warning("代码中未检测到几何基元的创建操作")


def _get_func_name(node: ast.Call) -> str:
    """从 ast.Call 节点提取函数名。"""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def build_fix_prompt(code: str, validation: ValidationResult) -> str:
    """
    构建让 LLM 自我修正的 prompt。
    """
    error_list = "\n".join(f"- {e}" for e in validation.errors)
    warning_list = "\n".join(f"- {w}" for w in validation.warnings) if validation.warnings else "无"

    return f"""你之前生成的 pyp3d 代码未通过验证，请修正以下问题后重新输出完整代码。

## 原始代码
```python
{code}
```

## 验证错误
{error_list}

## 警告
{warning_list}

## 修正要求
1. 修正所有错误
2. 输出完整的修正后代码（不要只输出修改部分）
3. 仍然只输出代码，不要多余解释
4. 必须以 from pyp3d import * 开头
5. 必须包含 create_geometry() 调用
"""
