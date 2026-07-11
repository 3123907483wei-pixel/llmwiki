# Transformer

> Transformer 是一种基于自注意力（Self-Attention）机制的深度学习架构，由 Vaswani 等人在 2017 年的论文 "Attention Is All You Need" 中提出。它完全摒弃了传统的循环和卷积结构，成为现代 NLP 和 AI 的基石。
>
> *最后更新: 2026-07-11 12:00 | 内容 ID: a1b2c3d4*

---

## 概述

Transformer 架构的核心创新在于**自注意力机制（Self-Attention）**，它允许模型在处理序列数据时，直接计算序列中任意两个位置之间的相关性，从而捕获长距离依赖关系。

## 核心要点

* 完全基于注意力机制，摒弃 RNN/CNN
* 支持大规模并行计算，训练效率极高
* 通过 [[Attention]] 机制捕获全局依赖
* 是 [[GPT]]、[[BERT]] 等大语言模型的基础架构

## 架构组成

### Encoder（编码器）
- 多头自注意力层（Multi-Head Self-Attention）
- 前馈神经网络（Feed-Forward Network）
- 残差连接与层归一化

### Decoder（解码器）
- 掩码自注意力层（Masked Self-Attention）
- 编码器-解码器交叉注意力
- 前馈神经网络

## 关联概念

[[Attention]], [[Self-Attention]], [[GPT]], [[BERT]], [[LLM]]

## 关键技术

### Scaled Dot-Product Attention

$$ \text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V $$

- $Q$: Query 矩阵
- $K$: Key 矩阵
- $V$: Value 矩阵
- $d_k$: 缩放因子（Key 的维度）

### Multi-Head Attention

将 Q、K、V 通过不同的线性投影映射到多个子空间，并行计算注意力，最后拼接结果。

## 参考文献

* Vaswani et al., "Attention Is All You Need", NeurIPS 2017
* 来源: LLM Wiki 知识编译系统

---

*此页面由 Ingest Agent 自动编译生成*
