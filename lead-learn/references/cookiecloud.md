# CookieCloud 配置与故障

## 服务端

已部署在 `https://<your-domain>`：

| 项 | 值 |
|---|---|
| 服务器 | `<server-ip>`（Ubuntu 22.04） |
| 运行时 | Node.js 20 |
| 监听 | `127.0.0.1:8088`（只回环，外部不可达） |
| 进程 | systemd `cookiecloud`，开机自启 |
| 证书 | Let's Encrypt，自动续期 |
| 数据 | `/opt/cookiecloud/api/data/<uuid>.json` |

> 真实域名与 IP 不入库（本仓是公开仓库）。实际值填在
> `$LEAD_LEARN_HOME/.favorites-out/cookiecloud.json` 里，不进版本控制。

运维命令见 `references/server-ops.md`（在项目仓里）。

## 凭据

存于 `$LEAD_LEARN_HOME/.favorites-out/cookiecloud.json`。

### 支持两种写法

**多账号（推荐）** —— 一份 profile = 一个浏览器 = 一个账号：

```json
{
  "profiles": [
    {
      "name": "edge-a",
      "host": "https://<your-domain>",
      "uuid": "<36 位或自定义字符串>",
      "password": "<32 位或自定义字符串>",
      "account": "A账号（Edge 日常）",
      "platforms": ["bili", "dy"],
      "preferred": false
    },
    {
      "name": "chrome-b",
      "host": "https://<your-domain>",
      "uuid": "...",
      "password": "...",
      "account": "比特毯子（Chrome 运营）",
      "platforms": ["bili", "dy", "xhs"],
      "preferred": true
    }
  ]
}
```

**单账号（旧）** —— 仍然认，不必急着迁移：

```json
{ "host": "https://<your-domain>", "uuid": "<36 位>", "password": "<32 位>" }
```

**这个文件含明文密码，`.gitignore` 已挡。** 改凭据时 `cc_config.set_credentials()`
会自动留一份 `cookiecloud.bak-<时间>.json`。

### 选哪一份

优先级：`--profile <名字>` > 环境变量 `LEAD_LEARN_CC_PROFILE`
> `~/.lead-learn/config.json` 的 `cc_profile` > `preferred: true`
> 唯一一份 > **报错**。

多份都没有 `preferred` 时**报错而不是替你挑**——挑错了就是拿 A 账号的 cookie
抓 B 账号的收藏夹，全程不报错，只是内容悄悄换了个人。

`preferred` 只认 JSON 的 `true`。写成字符串 `"false"` 等于**没有**标 preferred
（`bool("false") == True` 这个坑已经踩过）。

**重名 profile 直接报错。** 放过去的后果：`set_credentials` 按名字把所有同名项
都置 `preferred=True` → 写盘 → 之后任何 `select()` 都报「2 份都标了 preferred」，
用户只能手改文件。

### ⚠ 改凭据走 set_credentials，别手改

```python
import cc_config
cc_config.set_credentials("edge-a", password="<新口令>")
```

它做三件手改做不到的事：

1. **写盘前先验证新口令能解开服务端数据**（`_verify_remote`）。语法合法的错口令
   本地查不出来，只会在下次抓取时才炸——那正是「改密码后解不开」的场景。
2. **先写 `.tmp` → 回读校验 → `os.replace` 原子替换**。原文件始终是完整可用的
   旧版本，直到新内容确认无误。早先是「先写盘再回读」，校验失败时盘已经脏了。
3. 自动留 `cookiecloud.bak-<时间>.json`。

离线改配置或测试时传 `verify_remote=False`，生产路径不要关。

### ⚠ uuid / password 的形状不限

服务端只把 `uuid` 当目录名，什么形状都收。实测一个 20 字符的自定义串
（非 UUID 形状）返回 200 + 605 KB 真实数据、解密完好。

**初版曾按「36 位标准 UUID + 32 位十六进制」写死正则，把合法凭据判成非法拦下。
不要加回这种校验**，见 `tests/test_cc_config.py::test_non_uuid_shaped_uuid_is_accepted`。

### ⚠ 改密码之后

服务端数据是用 **旧口令** 加密存着的。你在扩展里改了密码但没重新同步时：

| 状态 | 现象 |
|---|---|
| 扩展改了密码，未重新同步 | 服务端还是旧口令的密文 → **旧口令能解，新口令不能解** |
| 改完密码后同步过一次 | 密文已用新口令重写 → **新口令能解，旧口令不能解**（`UnicodeDecodeError`） |

所以改完密码**必须两边一起改**：扩展设置页 + `cookiecloud.json`。
`cc_fetch.py` 解不开时会直接告诉你「password 与上传时不一致」，
不会假装成「服务端挂了」。

想确认新口令对不对，用只读的 `python cc_fetch.py show`；
`cc_verify.py` 会 POST 探针数据**覆盖**该 profile 的真实 cookie，别拿它当日常体检。

### ⚠ B站 UID 必须与 profile 成对配

`~/.lead-learn/config.json`：

```json
{
  "cc_profile": "edge-a",
  "bili_uid_by_profile": {
    "edge-a": "<A 账号的 B站 UID>",
    "chrome-b": "<B 账号的 B站 UID>"
  },
  "bili_uid": "<A 账号的 B站 UID>"
}
```

`BILI_UID` 的解析顺序：环境变量 `BILI_UID` > `bili_uid_by_profile[cc_profile]`
> `bili_uid` > 空。

**⚠ 缺 key 时不会回退到通用 `bili_uid`。** 这一条是刻意的：

`cc_profile` 指 `chrome-b`，而 `bili_uid_by_profile` 里只有 `edge-a`（漏填、拼错、
或按老文档只配了 `bili_uid`）时，回退会让 `BILI_UID` 变成**另一个账号**的 UID——
正是本节要消灭的错，换了个入口又回来。所以现在缺 key 就等于 `BILI_UID` 为空，
`paths.BILI_UID_PROBLEM` 里写明原因，抓取时明确报错。

**这一条确实会吵。** 但「配错了要吵，不要猜」和 `cc_config` 里「不替你挑 profile」
是同一条原则：静默抓错人的代价，远大于配置时必须填全。

**这个映射断了就会抓错人。** `bili_grab3.py` 抓之前会核对 cookie 里的
`DedeUserID` 与配置的 `BILI_UID`，不一致就警告。

## 浏览器扩展配置

| 字段 | 值 |
|---|---|
| 服务器地址 | `https://<your-domain>` |
| 用户 KEY | 上面 json 里的 uuid |
| 密码 | 上面 json 里的 password |
| 加密方式 | `Fixed IV` |
| **同步域名关键词** | `bilibili` 或 `douyin` |

## ⚠️ 同步域名关键词只填一个词

**这是实测踩出来的大坑。**

| 填法 | 结果 |
|---|---|
| `bilibili,douyin` | ❌ 当成一个整体字符串匹配 → 0 个 cookie |
| `bilibili douyin` | ❌ 同上 |
| `bilibili` | ✅ 匹配到所有含该词的域名 |
| 留空 | ⚠️ 能通，但**会把全部 526 个域名的 cookie 都传上去**，含邮箱/支付/GitHub |

扩展的匹配逻辑是「域名包含这个字符串」，不是关键词列表。

**留空的风险是真实的**：实测留空同步后，服务端收到 163 邮箱、QQ 邮箱、
支付宝、淘宝、百度网盘、Airwallex 支付、GitHub、Notion 等全部凭据。

## 加密协议

```python
key = md5(uuid + '-' + password)[:16]
plain = AES_decrypt(encrypted, key)   # CryptoJS 格式
data = json.loads(plain)              # {cookie_data, local_storage_data}
```

CryptoJS 格式 = `"Salted__"` + 8 字节盐 + AES-CBC 密文，
要用 EVP_BytesToKey(MD5) 派生 key/iv。

**实现在 `scripts/cc_crypto.py`，不要另写一份。** 这一层不依赖 `paths` / `cc_config`
（只做纯加解密 + HTTP），所以 `cc_config.set_credentials()` 能在写盘前用它验证口令，
而不会和 `cc_fetch` 形成循环 import。

依赖方向是单向的：

```
cc_fetch.py / cc_verify.py  →  cc_config.py  →  cc_crypto.py
     取数 + 格式                凭据解析校验       纯加解密 + HTTP
```

## 脱敏口径（硬约束）

| 东西 | 允许出现在输出里 |
|---|---|
| password | **只给长度**，一个字符都不给 |
| uuid | **只给长度**（`profile.safe_uuid()`）。它是服务端路径键 `/get/<uuid>`，泄露前缀等于缩小爆破空间 |
| 派生密钥 | 最多前 4 位，用于判断两次跑的是不是同一份凭据 |
| cookie 值 | 永不 |

要打 uuid 一律走 `profile.safe_uuid()`，别写 `uid[:8]` ——散着写总有地方会漏。
测试里也不许出现真实 uuid / B站 UID / 域名，用同形状假值。

## 域名键不是真实域名

设了关键词 `bilibili` 后，扩展回传的 `cookie_data` 键就是 **`"bilibili"`**，
不是 `.bilibili.com`。

```json
{"cookie_data": {"bilibili": [...48 个 cookie...]}}
```

所以导出时**按子串匹配键名**，不要写死域名列表。`cc_fetch.py` 已按此处理。

## 验证

```powershell
python scripts/cc_fetch.py profiles       # 有几份账号、哪些可用（只读，看这个先）
python scripts/cc_fetch.py show           # 看服务端有什么（只读）
python scripts/cc_fetch.py export bilibili
python scripts/cc_verify.py               # ⚠ 会 POST 覆盖，别当日常体检
```

**日常体检用 `profiles` / `show`，它们只读。**
`cc_verify.py` 会往服务端 POST 一份 `.test.local` 探针数据，**覆盖该 profile 的整份真实
cookie**；扩展下次同步会盖回来，但中间这段时间抓取拿不到登录态。

`show` 能正常列出域名 = 服务端、加密、凭据全对。若只有 `.test.local`，说明扩展没上传成功。

## 同一个命令两个结果 —— 别再犯

2026-11-24 之前，工作区（`$LEAD_LEARN_HOME`）里躺着 `cc_fetch.py` / `health.py` /
`cc_verify.py` 的**副本**，skill 里还有一份。凭据结构升级后 skill 版跟着改了、
工作区版没跟上，于是：

```
D:\Project\Test> python cc_fetch.py show          → KeyError: 'host'
<skill>\scripts> python cc_fetch.py show          → 正常列出域名
```

同一个命令，换目录两种结果，最费时间。现在工作区那三个文件是**转发壳**
（`runpy` 转给 skill），两边输出必然一致。

**判据：脚本只有一份真身，在 skill 里。工作区只放转发壳和数据。**

