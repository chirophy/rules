# 节点工坊 · Mihomo / Stash

浏览器节点转换器：粘贴 VMess、VLESS、Trojan、SS 链接，选择内核，生成并下载对应 YAML。

网站地址：[GitHub Pages](https://chirophy.github.io/rules/)。部署状态以仓库 Pages 设置和实际访问结果为准。也可下载仓库后打开 `index.html` 或 `model_new_updated.html`。

## 公开版与隐私

- 不内置真实节点、UUID、密码、服务器地址或订阅凭据；只生成用户当次输入的节点。
- 节点链接仅在浏览器内解析，不向服务器发送，不写入浏览器存储。下载的 YAML 包含你输入的凭据，请自行保管。
- Tailwind 已预编译成本地 CSS；无外部 JavaScript、分析或上报代码。Font Awesome 样式和 Google Fonts 仍从外部加载，加载这些资源会产生普通资源请求。CSP 禁止 fetch/XHR 等连接。
- 本地原始基准与私有备份不参与发布；公开的 `rules-baseline.yaml` 为删除节点内容后的分流基准。它与 `templates/*.yaml` 均不能直接导入客户端。

## 使用

1. 输入自己的节点链接，节点名须包含 `LA-VMRack-三网`、`LA-DMIT`、`LA-Zgo`、`JP-RFCHost`。这些名称被规则直接引用；缺失时停止生成。
2. 至少提供一个名称以 HK、MO 或 TW 开头的节点，填充港台地区组。日本、美国组按 JP/JPMAX、LA/SJC/DLS 前缀识别。公开版不再自动追加原页面的三个固定 IPv6 节点。
3. 选择 Mihomo 或 Stash，生成并下载配置，再导入对应客户端。切换内核后重新生成。

## 分流与平台边界

两端为 30 条规则、20 个远程集合、16 个策略组。保持规则顺序和默认出口：AI 候选依次为 LA-VMRack-三网、LA-DMIT、LA-Zgo；rfc.uhdnow.com 使用 JP-RFCHost；TikTok 默认美国；Steam 下载、微软、苹果默认直连。国内 UDP 443 + GEOSITE CN 直连，国外继续匹配后续规则。两个广告策略组保持独立；移除 reject 后广告覆盖减少。

Mihomo 使用 respect-rules，Stash 使用 follow-rule；两端开启顶层与 DNS IPv6。默认及节点 DNS 使用阿里、腾讯 DoH，国外 geosite policy 使用带策略组后缀的 Cloudflare、Google DoH。Mihomo 另有 direct-nameserver。Stash 的 DNS 策略组后缀和实际 IPv6 行为仍需客户端验证。

Stash 模板按用户要求增加 `unified-delay: true`、`tcp-concurrent: true`；已验证生成结果包含这两个字段，客户端实际行为尚未实机验证。

Stash 模板目标为 iOS/tvOS 3.6+、macOS 4.3+。iOS/tvOS 不支持进程规则。模板写入 `mixed-port: 7890`、`allow-lan: true`，局域网共享还需在客户端启用“允许局域网连接”。两端保留 `external-controller: 0.0.0.0:9090`；模板未配置管理密钥，导入前请按自身需求限制管理接口访问。Stash 是否采用该字段尚未实机确认。

结构检查通过不代表客户端启动或服务器连通性通过。未执行 Mihomo 内核启动和 Stash 实机导入测试；每个节点输出 `udp: true` 也不代表服务器支持 UDP。

## 维护与验证

```powershell
python -m pip install --target .tools -r requirements.txt
python scripts/build_templates.py
node scripts/test_converter.cjs
python scripts/validate_templates.py
python scripts/prepare_public.py
```

生成器同时更新两份独立模板、转换器与 Pages 入口。验证覆盖严格 YAML、重复键、节点和策略组引用、规则集引用、策略组环路、分流顺序、模板一致性、缺失节点阻止生成、输出转义和实际生成节点数量。测试仅使用虚构节点。

重新编译样式：

```powershell
npm exec --yes --package=tailwindcss@3.4.17 -- tailwindcss -c tailwind.config.cjs -i assets/tailwind-input.css -o assets/tailwind.css --minify
```

`prepare_public.py` 使用明确文件清单导出 `.publish/rules/`，排除原始基准、私有备份、缓存和依赖，扫描已知私有参数、UUID、令牌、私钥和带认证的 URL，并生成本地文件哈希清单。后续上传仍须使用该清单，不应直接上传整个本地目录。

`reports/` 保存公开上游规则集的历史统计与审查；快照不证明永久冗余，文本相等不等于完整语义覆盖。在线审计需联网，只读取公开规则源。

## GitHub Pages

Pages 发布来源使用 `main` 分支的 `/(root)`。`index.html` 为入口，`.nojekyll` 让 GitHub 直接发布静态文件。无需后端或账户凭据。

官方资料：[GitHub Pages 发布来源](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)、[Mihomo DNS](https://wiki.metacubex.one/config/dns/)、[Stash DNS](https://stash.wiki/features/dns-server)、[Stash 规则集](https://stash.wiki/en/rules/rule-set)、[Stash 局域网共享](https://stash.wiki/features/provide-proxy-to-lan-device)。协议转换逻辑尚未逐协议完成两端兼容审计。
