---
name: github-finder
description: 基于当前项目技术栈和需求，在GitHub上搜索可参考、可复用的开源项目。当用户需要：(1) 寻找类似功能的参考项目，(2) 查找可复用的轮子/组件，(3) 基于项目需求搜索开源解决方案，(4) 想要了解某个功能有哪些现成的开源实现时，使用此技能。
---

# GitHub 项目搜索助手

## 概述

此技能帮助你基于当前项目的技术栈、功能需求，在GitHub上搜索合适的开源项目作为参考或直接复用。

## 工作流程

### 步骤 1：分析项目上下文

首先分析当前项目的技术栈和需求：

1. **识别技术栈**
   - 查看 `package.json`、`Cargo.toml`、`requirements.txt` 等依赖文件
   - 识别框架（Vue、React、Nuxt、Next.js 等）
   - 识别主要语言（TypeScript、Python、Rust 等）

2. **理解需求**
   - 分析用户描述的功能需求
   - 提取关键技术关键词
   - 确定项目类型（博客、仪表盘、CLI工具等）

### 步骤 2：构建搜索策略

根据分析结果，构建有效的GitHub搜索查询：

**搜索语法参考：**
```
关键词 language:语言 stars:>最小星数
关键词 topic:主题标签
关键词 license:许可证
关键词 created:>日期 pushed:>日期
```

**搜索策略示例：**
- 按技术栈：`vue3 blog theme stars:>100`
- 按功能：`markdown editor language:typescript stars:>50`
- 按主题：`topic:nuxt3 topic:blog`
- 按许可证：`license:mit license:apache-2.0`

### 步骤 3：执行搜索

使用 WebSearch 工具搜索 GitHub 项目：

```
site:github.com 关键词 技术栈
```

### 步骤 4：筛选和评估

对搜索结果进行评估，关注：

1. **活跃度**：最近更新时间、issue处理速度
2. **成熟度**：stars数量、fork数量、贡献者数量
3. **文档质量**：README完整性、示例代码
4. **许可证**：MIT、Apache-2.0 等宽松许可证优先
5. **可复用性**：是否可作为独立模块使用

### 步骤 5：输出结果

按以下格式输出搜索结果：

```markdown
## 推荐项目

### 1. [项目名称](GitHub链接)
- **Stars**: xxx
- **描述**: 简短描述
- **技术栈**: Vue3, TypeScript, TailwindCSS
- **推荐理由**: 为什么适合当前项目
- **许可证**: MIT

### 2. ...
```

## 常用搜索模式

### 按项目类型搜索

| 项目类型 | 搜索关键词示例 |
|---------|--------------|
| 博客系统 | `blog theme`, `static site generator` |
| 管理后台 | `admin dashboard`, `admin template` |
| UI组件库 | `ui components`, `design system` |
| CLI工具 | `cli tool`, `command line` |
| API服务 | `api server`, `rest api`, `graphql` |

### 按技术栈搜索

| 技术栈 | 搜索示例 |
|-------|---------|
| Vue/Nuxt | `language:vue`, `topic:nuxt`, `topic:vue3` |
| React/Next | `language:jsx`, `topic:react`, `topic:nextjs` |
| TypeScript | `language:typescript` |
| Python | `language:python` |
| Rust | `language:rust` |

## 注意事项

1. **许可证兼容性**：确保开源项目许可证与项目需求兼容
2. **依赖冲突**：检查依赖版本是否与现有项目冲突
3. **维护状态**：优先选择活跃维护的项目
4. **代码质量**：查看代码结构、测试覆盖率等

## 参考资源

详细的GitHub搜索语法和API参考，请参阅 [references/github_search.md](references/github_search.md)。