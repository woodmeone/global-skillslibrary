# GitHub 搜索语法参考

## 基本搜索语法

### 按仓库搜索

| 限定符 | 示例 | 说明 |
|-------|------|------|
| `in:name` | `in:name vue` | 仓库名称包含关键词 |
| `in:description` | `in:description blog theme` | 描述包含关键词 |
| `in:readme` | `in:readme installation` | README包含关键词 |
| `in:topic` | `in:topic nuxt3` | 主题标签匹配 |

### 按语言搜索

```
language:typescript
language:vue
language:python
language:rust
```

### 按星数搜索

```
stars:>1000
stars:100..500
stars:<100
```

### 按时间搜索

```
created:>2023-01-01
pushed:>2024-01-01
```

### 按许可证搜索

```
license:mit
license:apache-2.0
license:bsd-3-clause
license:gpl-3.0
```

### 按用户/组织搜索

```
user:vuejs
org:microsoft
```

### 按主题搜索

```
topic:vue3
topic:nuxt
topic:blog
topic:tailwindcss
```

## 组合搜索示例

### 寻找Vue3博客主题

```
vue3 blog theme language:vue stars:>100 pushed:>2023-01-01
```

### 寻找TypeScript UI组件库

```
ui components language:typescript stars:>500 license:mit
```

### 寻找活跃维护的项目

```
nuxt3 theme pushed:>2024-01-01 stars:>50
```

### 寻找特定作者的优质项目

```
user:antfu stars:>100 language:typescript
```

## GitHub API 搜索

### 搜索仓库 API

```
GET https://api.github.com/search/repositories?q={query}
```

常用参数：
- `q`: 搜索查询
- `sort`: 排序方式 (stars, forks, updated)
- `order`: 排序顺序 (asc, desc)
- `per_page`: 每页结果数 (最大100)
- `page`: 页码

### 示例请求

```
https://api.github.com/search/repositories?q=vue3+blog+stars:>100&sort=stars&order=desc
```

## 搜索技巧

1. **排除关键词**：使用 `-` 排除不想要的结果
   ```
   vue blog -angular -react
   ```

2. **精确匹配**：使用引号精确匹配短语
   ```
   "static site generator"
   ```

3. **OR 组合**：使用 OR 组合多个条件
   ```
   vue OR nuxt language:typescript
   ```

4. **文件搜索**：搜索特定文件内容
   ```
   filename:package.json "vue":^3
   ```

5. **扩展名搜索**：按文件扩展名搜索
   ```
   extension:vue extension:ts
   ```

## 许可证说明

| 许可证 | 商用 | 修改 | 分发 | 专利 | 私用 |
|-------|-----|-----|-----|-----|-----|
| MIT | ✅ | ✅ | ✅ | ❌ | ✅ |
| Apache-2.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| BSD-3-Clause | ✅ | ✅ | ✅ | ❌ | ✅ |
| GPL-3.0 | ✅ | ✅ | ✅ | ✅ | ❌ |
| LGPL-3.0 | ✅ | ✅ | ✅ | ✅ | ✅ |

**推荐**：对于大多数项目，优先选择 MIT 或 Apache-2.0 许可证的项目。
