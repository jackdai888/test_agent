# 测试规则知识库

本目录包含各种测试场景的详细规则和最佳实践。

## 📁 目录结构

```
test_rules/
├── README.md              # 本文件
├── ad_testing/            # 广告测试规则
│   └── interstitial.md   # 插屏广告测试规范
├── functional_testing/    # 功能测试规则
└── best_practices/        # 最佳实践
```

## 📚 如何使用

### AI Agent 使用
当遇到不熟悉的测试场景时，使用 `search_knowledge_base` 工具：

```python
# 查询插屏广告测试规范
search_knowledge_base("插屏广告测试规范")

# 查询登录功能测试
search_knowledge_base("登录功能测试方法")

# 查询问题解决方案
search_knowledge_base("广告加载失败怎么办")
```

### 测试人员使用
1. 直接编辑 Markdown 文件添加新规则
2. 运行 `python knowledge_base.py` 重建索引
3. 新规则立即可用，无需修改代码

## 📝 编写规范

每个测试规则文档应包含：
1. **测试目标**：这个测试要验证什么
2. **前置条件**：测试前需要满足的条件
3. **测试步骤**：详细的操作步骤
4. **预期结果**：每步应该看到什么
5. **常见问题**：可能遇到的问题和解决方案

## 🔄 更新流程

1. 编辑或添加 Markdown 文件
2. 运行 `python knowledge_base.py` 重建索引
3. 测试搜索功能是否正常

## 📖 已有规则

- [插屏广告测试规范](ad_testing/interstitial.md)
- 更多规则持续添加中...
