# Issue · lead-learn 无人值守学习链路

## 用户故事

作为 YG，我想要 lead-learn 在我不在的时候也能稳定跑（抓取 → 处理 → 派单），
并且跑坏了能退回去、跑歪了能自己改，以便收藏夹里的东西不会因为我没空就积压成山。

## 背景 / 为什么要变

2026-11-24 实测出三件事，每件都有证据：

1. **「丢弃」的稿子每晚会被重新捞出来派一遍。** 台账记了 16 条丢弃，
   但 `cmd_apply` 从来没把源稿 `status:` 改成 dropped。已修，历史欠账已补。
2. **抓取窗口只有 40 条/平台，第 41 条以后永远学不到。** 目前 `processed`
   43 条里 0 条掉出窗口，说明还没撞上，但收藏速度 1.8 条/天，迟早撞。
3. **`clean` 只清 `route in (subtitle, asr)` 的 mp4。** 盘上现有 40.5 MB
   是 storyboard / no_speech 这几类，`clean` 一行都不删；其中一条 32.6 MB
   的民俗视频永远清不掉。不清的话按每天 40 条估算，一年 285～428 GB。

同时，自优化（跑完发现不合理就改 skill）目前**没有回滚能力**：
本 skill 与其所在的库都没有 `.git`。
自动改坏一个语法错，第二天整条链路哑掉且无人知晓。

## 验收标准

- [ ] `lead-learn` 是 git 仓库，`git log` 能追到每次改动，坏改动能 `git revert`
- [ ] `dispatch.py apply` 对 `dropped` / `undecided` 的稿子回写状态，
      重跑 `list` 不再返回它们（已有测试覆盖，需固化成仓库内测试）
- [ ] 抓取窗口可配置且默认值 > 40，`pipeline.py check` 不因窗口小而漏稿
- [ ] `clean` 覆盖 storyboard / no_speech / fail 的孤儿媒体，`--keep-mp4` 仍是真 dry-run
- [ ] `pipeline.py run` 有 `--dry-run`，不落盘、不下载
- [ ] 三个冒烟命令（dispatch status / health / pipeline status）任一失败
      时，自优化流程能拒绝提交并 revert
- [ ] 定时任务按方案配置，空跑时不留无用日志

## 票（垂直切片，按序实现）

- [ ] 票1：`git init` + 基线 commit + `.gitignore`（排除 `__pycache__`、`*.pyc`）
      ｜ Blocked by: 无
- [ ] 票2：`clean` 扩到孤儿媒体 + `run --dry-run`
      ｜ Blocked by: 票1
- [ ] 票3：抓取窗口参数化（`FAV_LIMIT` 默认 100）+ `bili_grab3.py` 与
      `favorites.py` 统一读同一个配置
      ｜ Blocked by: 票1
- [ ] 票4：仓库内测试（`tests/test_dispatch.py` / `tests/test_clean.py`），
      固化已修的 4 个 bug 为回归用例
      ｜ Blocked by: 票2、票3
- [ ] 票5：定时任务 + 自优化闭环（生成问题报告 → 人工或自动改 → 冒烟门禁）
      ｜ Blocked by: 票4

## 范围外（本轮不做）

- 不改 `SKILL.md` 的 `name` / `description`（改了触发 skill 目录刷新，风险高）
- 不动 `~/.midnight/recall` 记忆区（105 MB，搬走收益低）
- 不做程序化关键词打分分流（三次实测证明这条路是错的）
- 不接新平台

## 真相影响

- 新增 `PROJECT.md`（本 skill 当前真相：七步链路、脚本职责、数据布局）
- 新增 `CONTEXT.md`（术语表：staging 两义、dispatched/dropped/undecided、
  route 类型、agent 目录名 vs 显示名）
- ADR 需判三条：① `apply` 改成追加式（已做，难逆转吗？值得记）
  ② 定时频率选周还是日（真实取舍，值得记）
- `SKILL.md` 的「核活」节需按票2、票3 的实际行为更新
