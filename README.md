# 节点工坊 · Mihomo / Stash

浏览器节点转换器：粘贴 VMess、VLESS、Trojan、SS 链接，选择客户端，生成并下载对应 YAML。支持的输入协议保持不变；暂不解析 Mieru 链接或整份 YAML 节点输入。

当前转换器支持 TCP / WebSocket 传输；其他传输和 SS 插件参数会报告解析失败，避免生成缺少必要参数的节点。支持 UTF-8 的 VMess 名称、URL 转义的 Trojan 密码，以及 SS 的 Base64、明文转义、旧式整段 Base64 和带方括号 IPv6 地址。存在失败行时，仅输出成功解析的节点并提示失败数量；缺少规则必需节点时仍阻止生成。

网站地址：[GitHub Pages](https://chirophy.github.io/rules/)。部署状态以仓库 Pages 设置和实际访问结果为准。也可直接打开本地 `index.html`。

## 模板与隐私

当前 `rule-providers` 与完整有序 `rules` 以用户最新提供的 TXT 为准；DNS、策略组和中转交互保留已确认版本。公开的 `rules-baseline.yaml` 只包含分流设置、节点名称及链路名称映射；页面还叠加最新的地区默认规则和成员选择，不包含节点连接参数，不能直接导入客户端。`x-converter.dialer-proxies` 是转换器元数据，生成客户端配置时会移除。

- 不内置节点地址、UUID、密码或订阅凭据；只输出本次输入成功解析的节点。
- 节点链接仅在浏览器内解析，不上传、不写入浏览器存储。下载配置包含输入的凭据，请自行保管。
- 本地参考 YAML（包括仍保留部分连接参数的脱敏文件）、原始基准、私有备份均不参与公开导出。
- Tailwind 为本地 CSS；无外部 JavaScript、分析或上报代码。Font Awesome 样式和 Google Fonts 仍从外部加载，会产生普通资源请求。CSP 禁止 fetch/XHR 等连接。

## 使用

**不点击“设置中转节点”就不使用中转。** 不需要中转时，粘贴规则要求的节点链接后直接点击“生成完整配置”；无需读取或勾选中转成员，不写入 `dialer-proxy`，也不输出 HK/JP Route 组。各网站的代理/直连分流继续按规则执行，“不使用中转”不等于让所有流量走 DIRECT。

需要链式代理时，点击“设置中转节点”即启用中转，无需额外开关，再按下述可选步骤设置中转成员与落地节点。点击面板中的“取消中转”后隐藏设置区并忽略中转设置（包括无效或缺失的成员），再次点击“设置中转节点”后继续使用当前页面内存中的设置并校验。

1. 输入节点链接。AI 组需要 `LA-VMRack`、`LA-DMIT`、`LA-Zgo`；`rfc.uhdnow.com` 按本次参考文件固定使用 `JP-KFCHost`。名称必须完全一致，缺失时阻止生成。
2. 【仅开启中转时】读取节点后，分别在 HK Route、JP Route 区域勾选对应地区的中转成员，每组至少一个；HK Route 仅允许勾选名称含 HK 的输入节点，JP Route 仅允许名称含 JP 的输入节点（均不区分大小写）；不再限制为原固定名单。默认预选原模板中的 HK-HKC / HK-IPLC / HK-HKC-80M，以及 JP-DMIT / JP-IPLC / JP-GoMaMi / JPMAX-100TB / JP-ISIF / JP-RFCHost 中实际输入的节点。暂不支持 Mieru 链接本身的解析。
3. 【仅开启中转时】如输入 `LA-RN` 或 `SJC-VmShell`，默认需要同时输入 `SJC-V.PS`；也可在页面改选其他中转或取消中转。缺少实际使用的出口会停止生成。
4. 选择 Mihomo 或 Stash；需要中转时，点击“设置中转节点”，在每个落地节点右侧选择中转出口。可以选择其他输入节点、HK/JP Route，或“不使用中转”。“自动默认”采用下表规则；自定义节点也可以设置中转。
5. 点击生成后下载。改变输入、中转设置或客户端后，旧结果失效，必须重新生成；中转选择只保留在当前页面内存中，刷新页面后恢复默认。删除已选中转节点会报错，不会静默改成直连。点击“恢复默认设置”可清除成员勾选与中转设置，恢复原模板成员和地区自动默认。
6. 导入客户端后确认实际选择了“节点选择 → 自动选择”，避免旧选择记录继续停留在 DIRECT。

## 中转链路

`dialer-proxy` 表示连接该节点服务器时先经指定出口。客户端先连接中转节点，再连接落地节点，最终由落地节点访问目标。策略组候选仅列出实际输入的节点，不补入任何内置节点，也不使用其他地区或 DIRECT 冒充缺失出口。

| 节点条件 | 自动默认中转 |
| --- | --- |
| 已被勾选为任一 Route 组成员 | 不使用中转，直接连接此节点服务器 |
| 其他名称含 HK 的节点（不区分大小写） | 🇭🇰 HK Route |
| 其他名称含 JP 的节点（不区分大小写） | 🇯🇵 JP Route |
| LA-RN、SJC-VmShell | SJC-V.PS |
| MO-Mhyidc-V6 | 🇭🇰 HK Route |
| 其他节点 | 不使用中转 |

若名称同时包含 HK 和 JP，优先采用 HK。手动选择始终优先于自动默认；将某节点勾选为组成员，不会覆盖已经手动指定的中转，而会在生成时检查其是否造成循环。组成员内可配置额外中转，但必须保证所有候选分支均无循环。

按最新要求，JP-Mhyidc-V6 默认使用 JP Route；这覆盖了原参考文件中该节点使用 HK Route 的关系。HK-Mhyidc-V6 仍默认使用 HK Route。地区默认只针对成功解析的输入节点，不内置任何连接参数。成员按原始预选顺序排列，新增勾选的成员追加到候选末尾；生成结果可在客户端的手动 Route 组内切换。

修改节点输入后，成员勾选与手动中转仍保留在当前页面内存中；显式勾选的成员被删除时会显示缺失状态并阻止生成，可取消勾选或补回节点。开启中转时空组不会自动退回 DIRECT；取消中转时不输出这些组，也不要求成员。其他自定义节点可在页面中手动指定中转。

旧版日本/港台/美国地区测速组已按参考文件替换为两个手动 Route 组。主选择组默认为“自动选择”，DIRECT 保留为手动候选；其他业务组候选按参考名单筛选输入节点。TikTok 按本次参考文件默认跟随主选择组，未额外固定美国。

## 分流与平台边界

最新规则更新：BanAD 改用 blackmatrix7 AdvertisingLite，BanProgramAD 改用 Privacy；SteamCN、Microsoft、ProxyMedia 分别改用 blackmatrix7 的 SteamCN、Microsoft、GlobalMedia，五项均为 classical / YAML。移除远程 GoogleCN 集合，在原位置使用 `GEOSITE,google-cn,🎯 全球直连`。这些是按最新 TXT 指定的来源替换，不表示新旧规则覆盖完全相同。2026-10-23 检查时，19 个远程集合均成功下载并解析，快照见 `reports/rule-audit.json`；这不保证后续远程内容不变或客户端网络始终可达。

两端均为 30 条规则、19 个远程集合；中转关闭时为 13 个策略组，开启时为 15 个策略组。保持最新 TXT 中的完整规则顺序：进程、内网、国内 UDP 443 在自写规则前，AI 后为自写域名与 TikTok，再到广告、媒体和通用代理。Steam 下载、微软、苹果默认进入可切换的“全球直连”；部分国内规则直接使用 DIRECT，二者不是同一策略。两个广告组保持独立。

Mihomo 显式启用内置 DNS、Fake-IP 和 `respect-rules`；Stash 使用 `follow-rule`，不照搬 Mihomo 专用的 DNS 开关。两端保留 IPv6、默认/节点 DNS 的国内 DoH，以及参考文件中的国外 DNS 策略。Stash 对 `#策略组名` DNS 后缀的行为仍需实机确认，本次按参考文件保留，没有将其宣称为已验证兼容。

Mihomo 自动组显式使用 HTTPS 测试 URL；Stash 使用客户端默认测速设置。两端测速结果只代表测试目标的连通性与延迟，不保证 AI、流媒体解锁或服务器支持 UDP。

Stash 目标为 iOS/tvOS 3.6+、macOS 4.3+；iOS/tvOS 不支持进程规则。按参考文件输出 `mixed-port: 7890`、`allow-lan: true`、`unified-delay: true`、`tcp-concurrent: true`；字段存在不代表已开启客户端局域网共享或已实机验证。VLESS 按两端文档分别输出 Mihomo 的 `servername` 和 [Stash 的 `sni`](https://stash.wiki/proxy-protocols/proxy-types)。控制接口继续保留 `0.0.0.0:9090`，未配置管理密钥，应按使用环境限制访问。

## 维护与验证

```powershell
python -m pip install --target .tools -r requirements.txt
python scripts/build_templates.py
node scripts/test_converter.cjs
python scripts/validate_templates.py
python scripts/prepare_public.py
```

重新从本地参考文件同步时，使用 `python scripts/build_templates.py --source <本地参考文件.yaml>`。此操作只提取公开配置及节点名称间的中转关系，不复制 `proxies` 中的连接参数。单独更新规则时使用 `python scripts/build_templates.py --rules-source <最新规则.txt>`，只替换 `rule-providers` 和 `rules`，不修改 DNS、策略组或页面中转交互。可用 `python scripts/validate_templates.py --rules-source <最新规则.txt>` 检查与 TXT 完全一致。若同时更新完整参考文件和规则 TXT，可同时传入两个参数，TXT 的规则优先。普通生成只依赖公开基准，不需要本地参考文件。

生成器同步两份独立模板、网页内置模板和链路元数据；不要只手动修改生成结果。校验覆盖严格 YAML、重复键、引用、完整节点/策略组/中转图的循环、规则顺序、模板一致性、全量/最小/新增节点、缺失中转出口、空 Route 组、名称冲突、字符串转义、真实下拉与勾选事件、地区默认、按地区筛选组成员、自定义多级中转、取消中转、恢复默认，以及不开启中转时直接生成和忽略无效中转设置。测试仅使用虚构凭据与文档保留地址。结构验证不等于内核启动或 Stash 实机通过。

重新编译样式：

```powershell
npm exec --yes --package=tailwindcss@3.4.17 -- tailwindcss -c tailwind.config.cjs -i assets/tailwind-input.css -o assets/tailwind.css --minify
```

`prepare_public.py` 按明确清单导出 `.publish/rules/`，排除本地源文件、私有备份、缓存和依赖，扫描已知私有参数、UUID、令牌、私钥和带认证的 URL，并生成本地文件哈希清单。上传必须使用该清单，不能上传整个本地目录。`reports/` 是历史快照，不能证明当前远程内容或永久冗余。

## GitHub Pages

Pages 发布来源使用 `main` 分支的 `/(root)`；`index.html` 为入口，`.nojekyll` 用于静态文件发布。本次本地修改不代表已经部署。

官方资料：[Mihomo dialer-proxy](https://wiki.metacubex.one/config/proxies/dialer-proxy/)、[Mihomo DNS](https://wiki.metacubex.one/config/dns/)、[Stash DNS](https://stash.wiki/features/dns-server)、[Stash 规则集](https://stash.wiki/en/rules/rule-set)、[Stash 局域网共享](https://stash.wiki/features/provide-proxy-to-lan-device)。协议转换逻辑尚未逐协议完成两端兼容审计。
