# LLM

> Large Language Model（大语言模型）是指参数规模通常在数十亿以上的语言模型，基于 [[Transformer]] 架构，在海量文本数据上训练而成。代表模型包括 [[GPT]] 系列、[[BERT]]、LLaMA、Claude 等。
>
> *最后更新: 2026-07-11 12:00 | 内容 ID: e5f6a7b8*

---

## 概述

LLM 是当前 AI 领域的核心范式，其核心特征是**涌现能力（Emergent Abilities）**——当模型规模超过某个阈值后，会展现出小模型不具备的推理、规划和指令跟随等能力。

## 核心要点

* 参数规模通常在 1B 以上
* 基于 [[Transformer]] 架构，使用 [[Attention]] 机制
* 涌现能力：小模型没有，大模型突然具备的能力
* 推动了 Agent、RAG、AI 应用等生态发展

## 关键技术

### 1. Scaling Law
模型性能与三个因素呈幂律关系：
- 参数量
- 训练数据量
- 计算量（FLOPs）

### 2. 涌现能力
- 上下文学习（In-Context Learning）
- 思维链推理（Chain-of-Thought）
- 指令跟随（Instruction Following）

### 3. 对齐技术
- RLHF（基于人类反馈的强化学习）
- DPO（直接偏好优化）
- Instruction Tuning

## 代表模型

| 模型 | 公司 | 参数量 | 架构 |
|------|------|--------|------|
| GPT-4 | OpenAI | ~1.8T | [[Transformer]] Decoder |
| LLaMA-3 | Meta | 8B-405B | [[Transformer]] Decoder |
| Claude-3 | Anthropic | 未知 | [[Transformer]] Decoder |
| DeepSeek-V3 | DeepSeek | 671B | MoE [[Transformer]] |

## 关联概念

[[Transformer]], [[GPT]], [[BERT]], [[Attention]]

## 参考文献

* Kaplan et al., "Scaling Laws for Neural Language Models", 2020
* Wei et al., "Emergent Abilities of Large Language Models", 2022
* 来源: LLM Wiki 知识编译系统

---

*此页面由 Ingest Agent 自动编译生成*
