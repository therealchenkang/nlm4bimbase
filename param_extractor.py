"""
参数抽取与需求澄清（P0）— 在生成代码前先理清用户意图。

借鉴 StructureClaw 的 extract_draft_params + computeMissing + ask_user_clarification 范式：
对模糊输入（如"建一座房子"）先抽取已提供参数与缺失参数，缺失时带工程理由
反问用户或给出默认值，避免 LLM 静默脑补。
"""
import json
import re
import logging
from dataclasses import dataclass, field
from typing import Any

from config import EXTRACTION_USE_THINKING
from llm_client import LLMClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 系统 Prompt：让 LLM 做结构化的需求分析
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """你是 BIMBase 建模需求分析助手。分析用户的中文建模描述，判断要建什么、哪些关键尺寸/参数缺失。

# 分析步骤
1. building_type：判断建筑类型（单堵墙/方柱/圆柱/梁/板/框架/单层房屋/多层房屋/楼梯/基础/屋顶/门/窗/其他）
2. provided：用户已明确给出的参数（尺寸、数量、形式、材料等），**统一换算成毫米(mm)数值**
3. critical_missing：对该建筑类型**必须**、但用户未提供的关键参数。每项含：
   - key: 参数名(中文)
   - question: 向用户提问的完整问句
   - default: 合理默认值(数值)
   - unit: 单位(默认 "mm")
   - reason: 为什么给这个默认值(简短工程理由)
4. optional_missing：可选参数(有合理默认，无需打断用户)，结构同上

# 判断原则
- 单位换算：用户说"米/m" → ×1000 转 mm；"6米"=6000，"0.3米"=300
- **只有当输入足以直接生成完整代码时，critical_missing 才为空**
- 中文"尖屋顶/坡屋顶"通常指**双坡(人字形)屋顶**，不是四棱锥
- 不要把用户已提供的参数重复放进 critical_missing
- 默认值要符合建筑常识：墙厚200-300mm，层高3000mm，门2100×1200mm，窗1500×1200mm(窗台900mm)，住宅开间3000-8000mm，进深6000mm左右

# 输出格式
**只输出**下面这个 JSON（不要任何解释文字、不要 markdown 代码块外的内容）：
```json
{
  "building_type": "...",
  "provided": {"参数名": 数值或字符串, ...},
  "critical_missing": [
    {"key": "...", "question": "...", "default": 数值, "unit": "mm", "reason": "..."}
  ],
  "optional_missing": [
    {"key": "...", "question": "...", "default": 数值, "unit": "mm", "reason": "..."}
  ]
}
```"""


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class MissingParam:
    """缺失参数。"""
    key: str
    question: str
    default: Any
    unit: str = "mm"
    reason: str = ""


@dataclass
class ParamExtraction:
    """参数抽取结果。"""
    building_type: str = ""
    provided: dict = field(default_factory=dict)
    critical_missing: list = field(default_factory=list)      # list[MissingParam]
    optional_missing: list = field(default_factory=list)      # list[MissingParam]
    parse_ok: bool = True   # 抽取是否成功（失败时跳过澄清）

    @property
    def needs_clarification(self) -> bool:
        """是否需要向用户澄清（有 critical 缺失项且抽取成功）。"""
        return self.parse_ok and len(self.critical_missing) > 0


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------

def extract_params(client: LLMClient, user_input: str) -> ParamExtraction:
    """
    调用 LLM 抽取结构化参数。失败时返回 parse_ok=False（调用方应跳过澄清）。

    Args:
        client: LLM 客户端
        user_input: 用户的原始建模描述

    Returns:
        ParamExtraction 抽取结果
    """
    try:
        raw = client.generate(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_message=user_input,
            thinking=EXTRACTION_USE_THINKING,
        )
    except Exception as e:
        logger.warning(f"参数抽取 API 调用失败，跳过澄清: {e}")
        return ParamExtraction(parse_ok=False)

    data = _parse_json(raw)
    if data is None:
        logger.warning("参数抽取返回无法解析的内容，跳过澄清")
        return ParamExtraction(parse_ok=False)

    return _build_extraction(data)


def build_augmented_spec(
    user_input: str,
    extraction: ParamExtraction,
    resolved: dict,
) -> str:
    """
    组合用户原始输入 + 已确认参数，构造给代码生成阶段的增强描述。

    Args:
        user_input: 用户原始输入
        extraction: 抽取结果
        resolved: 用户确认/补充的参数 {key: value}

    Returns:
        增强后的建模需求描述
    """
    lines = [f"用户原始需求: {user_input}", ""]
    if extraction.building_type:
        lines.append(f"建筑类型: {extraction.building_type}")

    # 合并 provided + resolved，统一显示
    all_params = {}
    all_params.update(extraction.provided)
    all_params.update(resolved)

    if all_params:
        lines.append("已确认参数(请严格按这些数值生成，单位 mm):")
        for k, v in all_params.items():
            lines.append(f"  - {k}: {_normalize_to_mm(v)}")

    lines.append("")
    lines.append("请基于以上已确认参数生成完整的 pyp3d 代码。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
    """从 LLM 输出中健壮地解析 JSON。"""
    text = text.strip()

    # 1. 尝试提取 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = m.group(1) if m else text

    # 2. 兜底：找第一个 { 到最后一个 }
    if not candidate.strip().startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start:end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _build_extraction(data: dict) -> ParamExtraction:
    """从解析后的 dict 构建 ParamExtraction。"""
    def to_param(d):
        if not isinstance(d, dict):
            return None
        return MissingParam(
            key=str(d.get("key", "")),
            question=str(d.get("question", "")),
            default=d.get("default", ""),
            unit=str(d.get("unit", "mm")),
            reason=str(d.get("reason", "")),
        )

    critical = [p for p in (to_param(d) for d in data.get("critical_missing", [])) if p]
    optional = [p for p in (to_param(d) for d in data.get("optional_missing", [])) if p]

    return ParamExtraction(
        building_type=str(data.get("building_type", "")),
        provided=data.get("provided", {}) if isinstance(data.get("provided"), dict) else {},
        critical_missing=critical,
        optional_missing=optional,
    )


def _normalize_to_mm(val: Any) -> str:
    """把用户/LLM 给的值规范化成 mm 数值字符串。"""
    if isinstance(val, (int, float)):
        return f"{val} mm"
    s = str(val).strip()
    # "6米"/"6m"/"6 meter" → mm
    m = re.match(r"^-?([\d.]+)\s*(米|m|meter|M)\s*$", s)
    if m:
        try:
            return f"{int(float(m.group(1)) * 1000)} mm"
        except ValueError:
            pass
    return s
