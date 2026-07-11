# Attention

> 注意力机制（Attention）是深度学习中的一种核心技术，它允许模型在处理输入数据时，动态地关注最相关的部分。自注意力（Self-Attention）是 [[Transformer]] 的核心组件。
>
> *最后更新: 2026-07-11 12:00 | 内容 ID: b2c3d4e5*

---

## 概述

注意力机制的核心思想是：不是平等对待所有输入，而是根据当前任务的需求，有选择地关注输入中的重要部分。这类似于人类的视觉注意力——当我们看一张图片时，不会均匀关注每个像素，而是聚焦在关键区域。

## 核心要点

* 动态加权聚合输入信息
* 解决长序列建模中的信息瓶颈
* Self-Attention 是 [[Transformer]] 的核心
* 广泛用于 [[GPT]]、[[BERT]] 等模型

## 注意力类型

### 1. 加性注意力（Additive Attention）
- Bahdanau 等人提出
- 使用前馈神经网络计算注意力权重

### 2. 乘性注意力（Multiplicative Attention）
- Luong 等人提出
- 使用点积计算注意力权重

### 3. 自注意力（Self-Attention）
- Key、Query、Value 来自同一序列
- [[Transformer]] 的基础组件

### 4. 交叉注意力（Cross-Attention）
- Query 来自一个序列，Key/Value 来自另一个序列
- 用于 Encoder-Decoder 架构

## 数学定义

### 注意力的一般形式

$$ \text{Attention}(Q, K, V) = \text{softmax}(f(Q, K)) V $$

其中 $f$ 是注意力评分函数。

## 关联概念

[[Transformer]], [[Self-Attention]], [[GPT]], [[BERT]], [[LLM]]

## 参考文献

* Bahdanau et al., "Neural Machine Translation by Jointly Learning to Align and Translate", ICLR 2015
* Vaswani et al., "Attention Is All You Need", NeurIPS 2017
* 来源: LLM Wiki 知识编译系统

---

*此页面由 Ingest Agent 自动编译生成*
