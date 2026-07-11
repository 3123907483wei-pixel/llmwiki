# BERT

> Bidirectional Encoder Representations from Transformers（BERT）是 Google 于 2018 年发布的预训练语言模型。与 [[GPT]] 的自回归方式不同，BERT 使用 [[Transformer]] Encoder 和掩码语言建模（Masked Language Model）来实现双向上下文理解。
>
> *最后更新: 2026-07-11 12:00 | 内容 ID: d4e5f6a7*

---

## 概述

BERT 的核心理念是**深度双向预训练**。通过随机掩码一部分输入 Token，让模型从左右两侧的上下文中同时预测被掩码的词，从而学到更深层的语言理解能力。

## 核心要点

* 基于 [[Transformer]] Encoder 架构
* 双向上下文建模（区别于 [[GPT]] 的单向）
* 掩码语言建模（MLM）+ 下一句预测（NSP）
* 在 11 项 NLP 任务上刷新 SOTA

## 架构特点

### 1. 双向编码
与 [[GPT]] 的自回归（从左到右）不同，BERT 同时利用左右上下文。

### 2. 预训练任务
- **MLM**（Masked Language Model）：随机掩码 15% 的 Token
- **NSP**（Next Sentence Prediction）：判断两句话是否连续

### 3. 微调范式
预训练后，只需在特定任务上添加简单的输出层即可微调。

## BERT vs GPT

| 维度 | BERT | GPT |
|------|------|-----|
| 架构 | Encoder-only | Decoder-only |
| 方向 | 双向 | 单向（自回归） |
| 预训练 | MLM + NSP | 语言建模 |
| 擅长 | 理解任务 | 生成任务 |

## 关联概念

[[Transformer]], [[GPT]], [[LLM]], [[Attention]]

## 参考文献

* Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", NAACL 2019
* 来源: LLM Wiki 知识编译系统

---

*此页面由 Ingest Agent 自动编译生成*
