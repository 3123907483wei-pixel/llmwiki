# GPT

> Generative Pre-trained Transformer（GPT）是由 OpenAI 开发的基于 [[Transformer]] 解码器架构的大语言模型系列。GPT 采用"预训练 + 微调"范式，在海量文本数据上进行自监督预训练。
>
> *最后更新: 2026-07-11 12:00 | 内容 ID: c3d4e5f6*

---

## 概述

GPT 系列模型标志着大语言模型（[[LLM]]）时代的开端。其核心创新在于**缩放定律（Scaling Law）**——随着模型参数量、数据量和计算量的增加，模型能力呈现可预测的提升。

## 核心要点

* 基于 [[Transformer]] Decoder 架构
* 自回归语言建模（预测下一个 Token）
* 从 GPT-1 到 GPT-4，参数规模持续增长
* 推动了大模型（[[LLM]]）时代的发展

## 模型演进

| 版本 | 参数量 | 发布时间 | 关键创新 |
|------|--------|----------|----------|
| GPT-1 | 117M | 2018 | 证明 Transformer 预训练有效性 |
| GPT-2 | 1.5B | 2019 | Zero-shot 能力 |
| GPT-3 | 175B | 2020 | In-context Learning |
| GPT-4 | 估计 1.8T+ | 2023 | 多模态、推理能力 |

## 核心特性

### 1. 自回归生成
每次生成一个 Token，将已生成的内容作为下一轮的输入。

### 2. In-Context Learning
无需微调，通过 Prompt 中的示例即可适应新任务。

### 3. Scaling Law
模型性能与参数量、数据量、计算量之间存在幂律关系。

## 关联概念

[[Transformer]], [[LLM]], [[Attention]], [[BERT]]

## 参考文献

* Radford et al., "Improving Language Understanding by Generative Pre-Training", 2018
* Brown et al., "Language Models are Few-Shot Learners", NeurIPS 2020
* 来源: LLM Wiki 知识编译系统

---

*此页面由 Ingest Agent 自动编译生成*
