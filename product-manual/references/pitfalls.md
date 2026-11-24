# 截图与文档生成的坑（全部实测踩过）

## 截图

### dev 模式下 Cookie 被静默丢弃

**症状**：加购物车提示成功，进购物车还是空的；登录后刷新就退出。控制台无报错。

**成因**：项目为兼容预览 iframe 用了 `sameSite: 'none'`，但本地是 HTTP 没有 `Secure`，浏览器直接丢弃该 Cookie。加 `--disable-features=CookiesWithoutSameSiteMustBeSecure` 启动参数也无效（Chromium 158 实测）。

**解法**：不动项目代码，用 Playwright 直接注入 Cookie 绕过服务端下发环节：

```python
ctx.add_cookies([{
    "name": "tw_cart", "value": CART_ID,
    "domain": "localhost", "path": "/",
    "httpOnly": True, "secure": False, "sameSite": "Lax",
}])
```

购物车 ID 可先查库拿到，或直接构造一条测试数据。

### 签名 Cookie 需要复算

有些访问凭证是 `订单号~HMAC签名`。渲染页面前用同样的密钥算一遍：

```python
import hmac, hashlib, base64
sig = base64.urlsafe_b64encode(
    hmac.new(secret.encode(), f"buyer-order:{order_no}".encode(), hashlib.sha256).digest()
).decode().rstrip("=")[:22]
cookie = f"{order_no}~{sig}"
```

**陷阱**：下单动作会生成新订单号，需要在**跳转后**再补签一次，否则新订单页显示"无权限"。

### `next build` 因 Google Fonts 失败

离线或被墙时 `next/font/google` 直接让构建失败：

```
Failed to fetch Noto Sans SC from Google Fonts.
```

不要在 build 上耗时间，**直接用 `next dev` 截图**——渲染结果一致，还省了构建。

### pnpm shim 失效

```
'"...\pnpm\12.3.4\bin\\..\node_modules\pnpm\pnpm"' is not recognized
```

绕过：

```bash
node node_modules/next/dist/bin/next dev -p 3000
```

端口建议用 3000：很多项目在 dev 模式下把 `trustedOrigins` 写死为 `http://localhost:3000`，换端口可能导致登录态异常。

### 开发浮标污染截图

Next.js 左下角那个 "N Insight" 圆角浮标会出现在每张截图里。注入 CSS 隐藏：

```python
page.add_style_tag(content="""
nextjs-portal, [data-nextjs-toast], [data-nextjs-dev-tools-button],
#__next-build-watcher, nextjs-dev-tools-indicator { display: none !important; }
""")
```

注意：`add_style_tag` 在导航后失效，**每次 `goto` 之后都要重新注入**。

### Playwright 浏览器版本不匹配

```
Executable doesn't exist at ...chromium_headless_shell-1228\...
```

两种解法：`playwright install`，或直接指定已有浏览器：

```python
p.chromium.launch(executable_path=r"C:\Users\...\chromium-1254\chrome-win64\chrome.exe")
```

系统装的 Chrome 也能用，不必非用 Playwright 自带的那份。

## 文档

### 整页长图缩小后看不清

2880×5164 的整页截图塞进 15.5cm 宽的版面，字只有 2pt。**必须切分**：

```python
parts = 2 if ratio <= 3.2 else 3     # ratio = h / w
```

切完每段单独加图注（"图 1-1（下半）"），读者才知道是同一张图的延续。

### 图片体积失控

20 万像素级 PNG 每张 8MB，三份文档能到 60MB，Word 转 PDF 直接卡死 10 分钟无响应。

**处理**：长边压到 1240px（15.5cm @ 200dpi 足够），转 JPEG quality=86。

```python
im = Image.open(f).convert("RGB")
if im.width > 1240:
    im = im.resize((1240, int(im.height * 1240 / im.width)), Image.LANCZOS)
im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
```

体积从 8MB 降到 80KB，肉眼几乎无差别。

### 登录页截图大片留白

登录表单居中且窄，整页截图上下全是空白。按比例裁剪：

```python
im.crop((0, int(h * 0.27), w, int(h * 0.73)))
```

### Word COM 卡死

`Documents.Open` + `ExportAsFixedFormat` 在图片很大或文档很多时会静默挂住，PowerShell 进程一直不返回。

三道防线（见 `scripts/to_pdf.py`）：

1. `$word.DisplayAlerts = 0`
2. `subprocess.run(..., timeout=180)` 加超时
3. 超时后 `Get-Process WINWORD | Stop-Process -Force` 清残留

**重要**：一个文档卡死会让整轮任务超时，所以**先做好 DOCX 交付，PDF 作为最后一步批量补**。别在第一次转 PDF 时就把整轮任务压在它身上。

### 图片宽度失控：Cm 与 EMU 混用

**症状**：文档里的图宽 24cm，超出 15.5cm 正文宽，右侧被裁掉。

**成因**：常量写成 `CONTENT_W = Cm(15.5)`（已经是 EMU 数值），函数里又做一次 `Cm(width_cm)`，等于乘了两遍。

**修法**：常量存**纯数字厘米**，只在真正调用时转一次：

```python
CONTENT_W = 15.5                      # 纯数字

def _place_pic(doc, path, width_cm, max_h_cm, caption):
    width_emu = int(Cm(width_cm))     # 只在这里转
    if width_emu * ratio > int(Cm(max_h_cm)):
        width_emu = int(int(Cm(max_h_cm)) / ratio)
    run.add_picture(str(path), width=Emu(width_emu))
```

比较时两边都转 `int`，避免 `Cm` 对象与 float 混算的单位歧义。

**验证**（出稿前必做）：

```python
import zipfile, re
xml = zipfile.ZipFile(docx_path).read("word/document.xml").decode()
for cx, cy in re.findall(r'<wp:extent cx="(\d+)" cy="(\d+)"', xml):
    assert int(cx) / 360000 <= 15.6, f"图片超宽 {int(cx)/360000:.1f}cm，会被裁切"
```

### 改了工具库但输出没变

`docx_kit` 被反复导入时，`__pycache__` 里的旧 `.pyc` 会继续生效。改了代码但生成结果一模一样，先怀疑这个。

```powershell
Get-ChildItem -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force
```

验证实际生效的代码：

```python
import docx_kit, inspect
print(inspect.getsource(docx_kit._add_pic))
```

### 截图角落的中文乱码名

后台侧边栏底部通常显示当前用户名。若数据库 name 字段写入时编码错乱，截图会显示 `????`。

**先判断值不值得修**：这只是界面上一行小字，不影响任何操作说明。**除非客户会细看，否则别为它重截整套图**——重截 11 张 + 重生成文档 + 重转 PDF，成本远大于收益。

要修就一次做对：

```sql
update "user" set name='正确的名字' where email='...';
```

然后重跑截图脚本。别只重截一张——这批图里那行字都会出现，混着修好的和没修的反而更怪。

### 中文字体

`python-docx` 必须同时设两个位置，否则中文回落成宋体：

```python
run.font.name = "Segoe UI"
run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
```

段落样式同理，要在 `doc.styles["Normal"]` 上设一遍。

## 内容

### 后台里的技术词

按钮真写着「模拟」「mock」时，别为了好看改写成「测试」。照抄原文，但在开头加一句术语说明——读者看到界面上的「mock」和手册对不上会以为文档过时。

### 别把内部信息写进交付物

出稿前扫一遍：`localhost`、端口号、演示账号密码、`.local` 域名、测试数据中的真实人名电话。

```python
bad = ["localhost", "3000", "Demo12345", ".local", "assert", "TODO", "占位"]
```

### 界面语言 vs 正文字体语言

界面是繁体、正文是简体时，要主动向用户确认目标读者的语言。台湾买家看简体正文会有距离感；大陆商户看繁体界面截图则没问题——界面就是那个语言，改不了。
