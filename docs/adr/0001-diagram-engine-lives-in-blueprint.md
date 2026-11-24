# ADR-0001：画图引擎放在 codebase-blueprint，walkthrough 引用而非复制

- 日期：2026-11-24
- 状态：已采纳
- 取代：无
- 相关：[Issue #5](https://github.com/woodmeone/global-skillslibrary/issues/5)

## 背景

`codebase-walkthrough` 曾经同时承担两件事：**画图**和**写讲解**。它自己带一份渲染
引擎（`scripts/flow/renderer.js` 23.7 KB + `blueprint.css` 9.2 KB），734 行的
`build.mjs` 里约 163 行是画图、477 行是讲解。

问题不在体积，在 **framing**：因为唯一入口是「读懂陌生项目 → 出两个 HTML」，
画图能力被绑在了代码理解上。

- 用户说「帮我画个报销审批流程」，这个技能不会被唤起——description 里没有一个
  中文画图词。
- 即使唤起，输入契约要求 `diagrams + stories + sections`，画一张流程图也得先
  编造出场景案例和四问讲解。
- 纯画图那条路（`--diagram` 参数）是产品的**副产品**，SKILL.md 里没有一节讲它。

结论：**只能画 code 拆解那一张图。** 想画业务流程、ETL 管道、决策树，得先假装
自己在「读懂一个项目」。

历史上曾有一个独立的 `codebase-blueprint` 技能，后被合并删除。这次是反向操作，
但必须回答一个问题：**引擎怎么办？**

## 决策与取舍

**选：`codebase-blueprint` 独立成技能并拥有引擎；`codebase-walkthrough` 通过
`import` 引用它的 `core.mjs`，不持有副本。**

依赖方向单一：`walkthrough → blueprint`。反向无依赖。

```
community-skills/
├── codebase-blueprint/
│   ├── SKILL.md                     画图 skill（description 面向画图场景）
│   ├── assets/model.template.json
│   └── scripts/
│       ├── core.mjs                 validate / normalise / renderDiagramPage
│       ├── draw.mjs                 独立 CLI
│       └── flow/{renderer.js, blueprint.css, LICENSE.md}   ← 全局唯一一份
└── codebase-walkthrough/
    ├── SKILL.md                     讲解 skill（声明依赖）
    └── scripts/build.mjs            import core.mjs，把图包进文档
```

放弃了什么：

| 放弃的方案 | 为什么放弃 |
|---|---|
| **两个技能各带一份引擎** | 违反单一真相源。引擎升级必须改两处，迟早 drift。这正是上一轮被否掉的做法。 |
| **引擎放 `_shared/`** | 那不是 skill，harness 不会加载它，反而制造「这东西谁在用、怎么更新」的疑问。放在真正的使用者里更清楚。 |
| **保持一个技能，只改 description** | 零成本，但「画图」仍然是讲解的副产品。用户的诉求是「能画很多张不同的图」，不是「让画图更容易被发现」。 |
| **blueprint 依赖 walkthrough** | 依赖方向反了。画图不该知道讲解的存在。 |

代价与缓解：

- **两个技能必须同时安装。** 缓解：它们在本仓是兄弟目录，`SKILLS.md` 的接入脚本
  一起软链；`build.mjs` 启动时先检查 `core.mjs` 在不在，缺失则打印补救命令并
  exit 1，而不是抛 `ERR_MODULE_NOT_FOUND`。
- **相对路径 `../../codebase-blueprint/`** 依赖两者固定的兄弟关系。这是一个真实
  约束，写进了 `SKILLS.md` 和两边的 SKILL.md。

## 后果

**好的：**

- 画图成为一等能力。description 可以老老实实写「画流程图 / 画架构图 / 画状态机」，
  不再借「读懂项目」的壳。
- 引擎只有一份。修一次，两边都好。
- 讲解可以专注在它真正难的部分：元素抽象、链路编排、场景案例、边覆盖率。
- `build.mjs` 从 734 行降到 633 行，且剩下的都是讲解相关的。

**坏的：**

- 安装步骤多一条 junction，且漏装 blueprint 会让 walkthrough 不可用（已用明确的
  报错缓解）。
- `core.mjs` 成了事实上的公共 API，改它的签名要同时看两边。
- 拆分时最大的风险是「抽函数抽坏了」。缓解手段是**字节级回归**：重构前后四个产物
  （智愿真实数据的讲解页/图页、模板的讲解页/图页）SHA-256 完全一致。

**后来者要注意：**

- 想加新的渲染能力（比如新节点样式），改 `codebase-blueprint`，不要动
  `codebase-walkthrough`。
- 想改讲解结构（场景案例、四问卡、覆盖率），改 `codebase-walkthrough`。
- 判断归属的问法：**这件事需不需要知道「业务语义」？** 不需要 → blueprint。
