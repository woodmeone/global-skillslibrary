# 踩坑清单

全部实测踩出来的。改代码前先读一遍。

## B站

**1. `/x/v3/fav/resource/list` 会吃 HTTP 412 风控**
返回 HTML 页面不是 JSON。加节流（700-1200ms）和重试都无效。
→ 改用 `/x/v3/fav/resource/ids`（只返回 id 列表，语义轻，不风控）。

**2. `resource/ids` 返回的是夹内顺序，不是全局时间序**
直接取前 40 条会全来自最大那个收藏夹。
→ 两轮取：先每夹 2 条铺开覆盖，再回头补齐。

**3. 分页别用 `len < 20` 判断结束**
B站对部分夹子每页返回数不稳定（实测默认收藏夹某页只返 18 条）。
→ 用 `has_more` 字段。

**4. `/x/space/wbi/acc/info` 需要 WBI 签名**
匿名调用返回 `code: -352`（风控）。
→ 改用 `/x/web-interface/card?mid=`，不需要签名。

**5. 匿名查收藏夹列表返回 `data: null`**
不是「没有收藏夹」，是「看不到」。
→ 判断有无收藏夹用 `/x/space/navnum?mid=` 的 `favourite.master` 字段。

**6. 字幕检测别找表头 "zh"**
`yt-dlp --list-subs` 输出里表头是 `Language Formats`，`zh` 只出现在数据行
（`ai-zh  srt`）。→ 逐行找语言标记。

**7. `-q 480` 对竖屏无效**
竖屏 height 是 852，`height<=480` 筛不到任何格式，报 `Requested format is not available`。
→ 用 `best`。

**8. 匿名拿不到部分稿件的 480p**
→ 必须带 `--cookies`。

**9. 标题含 `/` 时 yt-dlp 会替换成 `⧸`**
用原始标题匹配已下载文件会失败。
→ 归一化后取前 12 字比对。

## 抖音

**10. `/video/` 会 302 到 `/note/`（图文笔记）**
素材不在 `douyinvod.com`，而在 `douyinstatic.com`。
→ 拦截白名单要同时覆盖两个域名。

**11. `douyinstatic.com` 也托管 css/js/图片**
第一批候选可能是 24KB 的 `static-style.css`。
→ 必须校验 `content-type`。

**12. 图文笔记可能只有音频**
`content-type: audio/mp4`，没有视频流。
→ 接受音频产物（存 `.m4a`），纯配乐无语音记 `no_speech`。

**13. 长视频是 blob: 包装的 DASH 分离流**（最关键）
`<video>.src` 只是 `blob:https://www.douyin.com/xxx`，拿不到真实地址。
真实地址在 `performance.getEntriesByType('resource')` 里。

**14. 音视频是两个独立 URL，content-type 都是 `video/mp4`**
只能靠 URL 里的 `media-video-` / `media-audio-` 标记区分。
只取一个会得到「有画面没声音」，转录直接报
`file does not contain any stream`。
→ 分别下载再用 ffmpeg `-c copy` 合并。

**15. `video` 元素可能有两个**：一个 blob 包装的真视频、一个空的占位。
→ 用 `performance` 资源而不是元素属性。

**16. `douyinvod.com` 媒体地址要 Referer + UA**
缺一即 403。
→ 补 `Referer: https://www.douyin.com/` + 浏览器 UA + `Range: bytes=0-`。

**17. 返回 206 是成功**
`Range` 请求的正常响应。别用 `!= 200` 判失败。

**18. 无头模式必撞验证码**
`title=验证码中间页`。→ 登录流程必须 headed。

**19. yt-dlp 拿不下抖音**
缺 `msToken`（运行时生成的会话 token，导出 cookie 也带不出来）。
→ 必须 Playwright 拦媒体。

## 处理

**20. 必剪 412 是瞬时限流**
退避重试能过，别一次失败就换方案。
→ 60s / 120s / 180s 三次重试。

**21. 「转录产物 > 200 字节」这个阈值是错的**
抖音短视频 10 秒级，转录只有 40-50 字（约 150 字节），会被误判失败，
白跑 storyboard。
→ 改为「存在且非空」，质量交给下游判断。

**22. storyboard 对长视频极慢**
39 分钟视频用了 17 分钟，1477 秒的直接跳过。
→ 设 600s 阈值，超了就标 `needs_manual`。

**23. 文件名里的换行符会炸 `write_text`**
抖音标题常带 `\n`，报 `OSError: [Errno 22] Invalid argument`。
→ `re.sub(r'[\\/:*?"<>|\r\n\t]+', "_")`。

**24. `clean --keep-mp4` 早期版本真删文件**
dry-run 分支写在了删除之后。→ dry-run 必须 `continue`。

**25. mp4 必须清**
17 条占 2.2 GB，其中一条合集 1.4 GB。拿到文本后 `clean` 释放 99%。

**26. 下载产物匹配不能用「目录里最新」**
会拿到别的视频。
→ 用「本次新增文件」或标题前缀匹配。

## 服务器 / 传输

**27. 宝塔的 nginx 不认 `/etc/nginx/sites-enabled/`**
实际在 `/www/server/panel/vhost/nginx/`，二进制是 `/www/server/nginx/sbin/nginx`。
→ 动 nginx 前先 `ps aux | grep nginx`。

**28. certbot webroot 会被反代吃掉**
`.well-known/acme-challenge/` 必须写在 `location /` 之前。

**29. 宝塔 nginx 不支持 `http2 on;`**
用老语法 `listen 443 ssl http2;`。

**30. CookieCloud 默认绑所有网卡**
`app.listen(port)` → `*:8088`。
→ 改 `app.listen(port, "127.0.0.1", ...)`。

**31. PowerShell → ssh 有三个坑**
CRLF（`$'\r': command not found`）、引号被吃、嵌套 heredoc。
→ 脚本转 LF → base64 编码 → 远端解码到 /tmp 再执行。

**32. PowerShell 写的 JSON 带 BOM**
`json.loads` 报 `Unexpected UTF-8 BOM`。
→ 读用 `utf-8-sig`。
