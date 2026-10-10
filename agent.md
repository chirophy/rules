# 项目维护约定

## 文件与事实来源
- `rules-baseline.yaml` 是公开分流基准；它不包含节点配置，不能直接导入客户端。本地原始 `rules-merged.yaml` 仅作对照，必须排除发布。
- `model_new_updated.html` 是节点转换器；`index.html` 是生成器同步的 Pages 入口，不单独编辑。
- `templates/mihomo.yaml`、`templates/stash.yaml` 是占位符模板；先修改 `scripts/build_templates.py`，再运行生成器同步所有输出。
- `README.md` 记录当前行为和兼容性边界，`reports/` 中远程规则快照只证明采集时的事实。

## 必须保留的分流语义
- 保持规则先后顺序；进程、内网和国内 UDP 443 在自写规则之前。
- AI 选择组候选依次为 LA-VMRack-三网、LA-DMIT、LA-Zgo；rfc.uhdnow.com 固定到 JP-RFCHost，不能静默替换。
- 保留 linux.do、open.cd、clash.razord.top、yacd.haishan.me 和 Bilibili 真实 IP 过滤项。
- TikTok 位于 AI 之后、媒体与通用代理之前，默认美国；Steam 下载、微软和苹果默认直连。
- 国内 QUIC 实际匹配 UDP 443 + GEOSITE CN；国外继续后续规则，不能统一拒绝。
- 全球直连是可切换策略组，不等价于 DIRECT；不同广告组不能因默认均 REJECT 而合并。
- 无内置固定节点，只使用输入的节点；缺少固定规则引用或港台地区节点时阻止生成。

## 平台适配与隐私
- DNS 字段分别使用 Mihomo respect-rules、Stash follow-rule；按官方文档核实，不依赖未知字段被忽略。
- Stash 目标为 iOS/tvOS 3.6+、macOS 4.3+，进程规则仅在支持的平台生效。
- Stash 保留 mixed-port: 7890、allow-lan: true；不把字段存在说成已经开启客户端局域网共享。
- 不在源码、测试、文档、日志或发布文件中添加真实密码、UUID、服务器参数和订阅凭据。测试使用保留文档地址及虚构参数。
- 不加载外部 JavaScript，不发送或持久化用户输入；将输入转义后再插入 DOM。
- 公开导出只使用 `scripts/prepare_public.py` 明确清单；`.private`、`.cache`、`.tools`、原始基准都不能上传。

## 验证与交付
- 检查严格 YAML、重复键、节点/策略组/规则集引用、环路、占位符残留和两端规则顺序。
- 校验独立模板、HTML 内置模板和 Pages 入口一致；用虚构节点测试缺失分支和仅输出输入节点。
- 不凭名称相似删除远程规则集；区分文本重复、语义覆盖、优先级和策略差异。
- 区分静态检查和真实客户端验证；未运行内核或实机导入时，不声称实机通过。
