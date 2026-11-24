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

存于 `$LEAD_LEARN_HOME/.favorites-out/cookiecloud.json`：

```json
{
  "host": "https://<your-domain>",
  "uuid": "<36 位>",
  "password": "<32 位>"
}
```

**这个文件含明文密码，不要进版本控制。**

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
要用 EVP_BytesToKey(MD5) 派生 key/iv。实现见 `scripts/cc_fetch.py`。

## 域名键不是真实域名

设了关键词 `bilibili` 后，扩展回传的 `cookie_data` 键就是 **`"bilibili"`**，
不是 `.bilibili.com`。

```json
{"cookie_data": {"bilibili": [...48 个 cookie...]}}
```

所以导出时**按子串匹配键名**，不要写死域名列表。`cc_fetch.py` 已按此处理。

## 验证

```powershell
python scripts/cc_verify.py             # 上传→取回→解密 全链路
python scripts/cc_fetch.py show         # 看服务端有什么
python scripts/cc_fetch.py export bilibili
```

`cc_verify.py` 通过说明服务端、加密、凭据全对。若 `show` 只有你自己的测试数据，
说明扩展没上传成功。
