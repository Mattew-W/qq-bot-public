#!/bin/bash
# 初始化数据目录

mkdir -p data/knowledge
mkdir -p data/analysis
mkdir -p data/rules
mkdir -p logs

# 创建示例知识库文件
cat data/knowledge/welcome.md << 'EOF'
# 欢迎使用 QQ Bot Framework

## 功能介绍

### 1. AI 问答
- @机器人 即可开始对话
- 支持知识库检索
- 支持上下文对话

### 2. 智能反垃圾
- 自动检测垃圾消息
- 支持规则和 AI 双重检测
- 自动处理违规用户

### 3. 数据分析
- 使用 /analyze 命令分析数据
- 支持 CSV/Excel/JSON 格式
- AI 驱动的智能分析

## 联系方式
如有问题，请联系管理员。
EOF

echo "数据目录初始化完成！"
