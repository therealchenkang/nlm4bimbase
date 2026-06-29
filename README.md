# BIMBase 自然语言建模工具

## 快速开始

开始之前应当安装相应的库，例如：openai

### 1. 设置 API Key

直接写入 `config.py`

```python
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxx"
```

### 2. 启动工具（我用的是mamba发行包，它用法和conda一样）

首先在powershell中进入bimbase\TEST文件夹

```cd /d <项目解压目录>\TEST```

然后运行命令

```bash
mamba run -n <环境名> python main.py
```

### 3. 输入描述

```
请输入建模描述 > 建一堵长6米厚0.3米高3米的墙
```

系统将自动生成 pyp3d 脚本并保存到 `output/` 目录。

### 4. 在 BIMBase 中运行

将生成的 `.py` 文件复制到 BIMBase 脚本目录，或在 BIMBase 中直接加载执行。

## 示例输入

| 描述 | 预期效果 |
|------|----------|
| 建一堵长6米厚0.3米高3米的墙 | 6000×300×3000 墙体 |
| 创建一根圆柱柱子，半径300mm，高4米 | 圆柱 (Cone) |
| 建一个三层框架，跨度6米，层高3米 | 嵌套循环生成柱+梁 |
| 在墙上开一个1.5m宽2m高的门洞 | 墙体布尔差集 |
| 创建一个L型建筑，两翼各6米 | Combine 组合两段墙体 |
| 建一个12级的楼梯，踏步宽300高150 | 循环 Combine 阶梯 |

## 命令

| 命令 | 说明 |
|------|------|
| 输入建筑描述 | 生成 pyp3d 脚本 |
| `quit` / `exit` | 退出程序 |
| `help` | 显示帮助信息 |

## 文件结构

```
bimbase/TEST/
├── config.py              # 配置（API key、模型、路径）
├── main.py                # CLI 交互式入口
├── llm_client.py          # DeepSeek API 客户端（思考模式）
├── system_prompt.py       # 系统 prompt（pyp3d API 文档 + 建筑模式库）
├── code_validator.py      # 代码验证器（语法 + 导入 + 模式检查）
├── output/                # 自动生成的脚本输出目录
└── reference/             # 参考脚本（few-shot examples）
    ├── wall.py
    ├── column.py
    ├── beam.py
    ├── slab.py
    ├── frame.py
    ├── opening.py
    ├── stairs.py
    └── foundation.py
```

## 配置说明

编辑 `config.py` 可调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | LLM 模型 |
| `LLM_TEMPERATURE` | `0.0` | 生成温度 |
| `LLM_TIMEOUT` | `180` | API 超时（秒） |
| `LLM_MAX_RETRIES` | `3` | API 调用失败重试次数 |
| `LLM_MAX_VALIDATION_RETRIES` | `3` | 代码验证失败后 LLM 自我修正轮数 |
| `ENABLE_CLARIFICATION` | `True` | 开启需求澄清环节（关闭则单轮直出） |
| `EXTRACTION_USE_THINKING` | `False` | 参数抽取是否启用思考模式 |

## 工作流程

```
用户输入中文描述
    ↓
[需求澄清] LLM 抽取参数 → 计算 criticalMissing
    ↓ 有缺失项(如"建一座房子"没给尺寸)
展示带工程理由的默认值 → 用户 [Y]用默认/[n]自填/[s]跳过
    ↓ 构造增强需求描述
调用 DeepSeek API（思考模式）生成 pyp3d 代码
    ↓
三层验证（语法 → 导入 → 模式）
    ↓ 验证通过            ↓ 验证失败
保存脚本文件          反馈错误给 LLM 自我修正（最多3轮）
    ↓
用户在 BIMBase 中加载运行
```

### 需求澄清（处理模糊输入）

对"建一座房子采用尖屋顶"这类没有精确尺寸的输入，系统会先抽取参数并列出缺失项：

```
[分析需求...]
  推断建筑类型: 单层房屋
  已提供参数:
    - 屋顶形式: 双坡屋顶(尖屋顶)
  缺少关键参数(已附默认建议):
    1. 房屋长度 — 默认: 8000mm  (单层住宅常见开间)
    2. 房屋宽度 — 默认: 6000mm  (常见进深)
    3. 层高 — 默认: 3000mm  (住宅常用层高)
    ...

  [Y]使用默认值 / [n]自己填写 / [s]跳过澄清直接生成 >
```

输入已完整（如"建一堵长6米厚0.3米高3米的墙"）时自动跳过澄清，直接生成。

### 复合构件模式库

`reference/` 与系统 prompt 内置以下复合构件的正确构造，避免几何盲区：

- **双坡(人字形)屋顶** = 三棱柱（三角形截面 Extrusion），中文"尖屋顶"默认按此处理
- 四坡屋顶（Loft 放样）、门洞+门扇、窗洞+玻璃、地面板、完整房屋（墙+门窗+屋顶+地面）

> 关键规则：颜色 `.color()` 必须在所有布尔运算(`+`/`-`)之后再赋值，否则会被 Fusion 对象丢弃。
