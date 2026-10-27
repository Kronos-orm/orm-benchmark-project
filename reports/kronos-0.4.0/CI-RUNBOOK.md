# CI 实验与不可变制品协议

状态：2026-10-27。candidate7本地临时API编译已通过；未启DB、未执行正确性、pilot、测量或profile。首次build-only CI已通过；正式artifact复用、DB门禁及测量仍待实际验证，正式实验等待主任务批准SHA。

## 工作流与阶段

experiment.yml支持PR→main的build-only入口，以及手动build/validate/pilot/measure。PR入口临时读取codex/kmp-continuation仅作编译适配；手动kronos_ref默认main，支持分支/tag/SHA。输入先通过GitHub commits API解析为唯一40位SHA，producer只checkout该SHA，下游不重复解析移动分支。版本guard要求Kronos0.4.0和Kotlin2.4.21；报告保留实际源码SHA，不将特性分支当已发布tag。

1. resolve冻结Kronos/benchmark SHA、JDK、MySQL image digest和780单元计划。
2. build/validate/pilot的producer在JDK21执行一次`scripts/run release jvm-stage --repository build/benchmark-candidate`及check-candidate，接着一次Gradle构建全部适配器/JDBC/JMH。两个release子命令均清除ambient GITHUB_SHA并显式传入resolve得到的KRONOS_SOURCE_SHA，避免跨仓库将benchmark SHA误标为Kronos SHA；pack再次核对candidate manifest.sha。lockfiles、candidate manifest/JAR、runtime classes/resources/JAR摘要、源码快照进入bundle；seal SHA通过job output传递。正式measure的producer仅下载/核验已审阅pilot run的同一bundle，不再次编译。
3. preflight只下载并校验bundle，无checkout/Gradle/Kotlin编译。独立MySQL中validate核对SQL、列、绑定、结果、commit、连接生命周期；pilot模式另跑8场景×6框架短跑。pilot自动保存真实warmup/iteration统计及正确性/完成marker摘要，作为后续判断预热和噪声的证据，不另设用户批准步骤。
4. measure为8场景组×5独立block=40job，max-parallel4；每job执行其block内全部六适配器，框架/场景顺序按固定seed随机。每case命令-f1，总计26场景×6框架×5block=780，不在shard内再扩五fork。
5. aggregate以always条件运行，汇总全部可得shard；只接收同一seal/源码/候选，拒绝重复、越界、错误分片与摘要不符。完整780单元缺失列表、FAIL/NOT_RUN与raw JSON/CSV/日志留存。可用数据生成部分分析；零成功只生成状态，不产生数字或空图。

## 固定环境与边界

JDK固定Eclipse Temurin21.0.10+7；runner标签ubuntu-24.04，每job记录ImageVersion、kernel、CPU、内存、JDK、五秒vmstat空闲基线及MySQL配置。MySQL固定官方`mysql:8.0.46@sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b`，清单/查询时间见versions/upstream/mysql-ci-image.json和[官方8.0.46说明](https://dev.mysql.com/doc/relnotes/mysql/8.0/en/news-8-0-46.html)。全部六适配器共享Connector/J9.7.0和Druid1.2.28。

每job独立MySQL容器/数据，127.0.0.1:13307，buffer pool256MiB、READ-COMMITTED、UTC、utf8mb4_bin、flush-at-commit1、关闭binlog。临时随机密码仅RUNNER_TEMP私有文件，mode600，值不进入argv/log/artifact。CI容器脚本限制GITHUB_ACTIONS=true，不操作本机DB。

GitHub hosted runner是虚拟机；相同标签不保证同一物理硬件、频率、热状态或邻居负载。**同一场景/block六适配器共享同一runner VM/DB**，分析前强制校验host证据与pairingUnit。不同场景可能来自不同VM，不把跨场景差值当固定物理机CPU实验；按场景报告paired ratios、全部5个fork点与host分布。iteration先在fork内求均值，不当独立样本。CI结果不宣称本机受控硬件或第三方认证。

## 正式运行门禁

先通过build/validate/pilot。审阅warmup轨迹、写入single-shot预热充分性、异常/方差、host基线，记录具体findings和pilot URL。measure必须同时提供：

- expected_kronos_sha：主任务批准的最终40位SHA，resolve须完全相等。
- producer_run_id：已完成48单元pilot的原构建run ID；下载该run的runtime-bundle和preflight，核对validation gate、pilot完成状态、48个PASS/raw摘要。
- 原pilot artifact中的pilot-review.json自动记录实际48单元的warmup、均值/中位数/CV、raw摘要、validation/completion marker摘要与run URL；producer逐项核验，不要求用户口令或ACCEPTED字段。

源码/lock/runtime字节变化使旧pilot review失效。measure所选benchmark ref必须仍指向pilot的同一benchmarkGitSha；不得在pilot审阅后移动该源码ref。JAR容器时间戳可能使重建字节变化，因此正式测量复用原artifact，不依赖两次重建恰好相同。原producer run ID和本次execution run ID分别记录。失败分片不静默重跑择优；重试保留新run ID及原因。当前尚无pilot数据，不能预填统计；正式measure仅需显式mode、expected源SHA和已验证pilot原bundle，发布保持独立。

仓库默认分支目前为result。PR已注册experiment workflow ID398381230，实测numeric dispatch可以在源码feature ref运行，无需修改默认分支或result内容。构建示例：`gh workflow run 398381230 --repo Kronos-orm/orm-benchmark-project --ref codex/reproducible-040-benchmark-ci -f mode=build -f kronos_ref=codex/kmp-continuation`。选择validate/pilot/measure须按对应阶段授权；正式measure仍需全部门禁。

## 报告与发布

aggregate仅上传待审阅artifact；真实分析经export_publication/validate_publication生成同一canonical结果的双语readme、详细分析、HTML/JSON与按需场景数据/图。官网主入口保持result/readme.md，所有链接绝对URL，根入口最多3张预先注册图。host/coverage证据随报告导出。

benchmark.yml仍为独立手动已审阅bundle发布任务，矩阵不调用它；不改主仓docs，不自动部署result。

## 真实凭据扫描与官网导出

每个DB job结束时，在RUNNER_TEMP生成的真实benchmark/root密码仍存在时扫描gate/pilot/shard全部待上传字节及zip/tar成员。secret-audit.json只包含candidate/source/benchmark/run/stage/group/block、各文件SHA256与cell身份，不含密码或密码摘要。scan失败删除receipt，上传step不会执行；不能先上传含secret文件再补检查。

aggregate先校验每份receipt的精确文件集合、字节与run身份，再复制数据；原始status保持逐字节不变，host路径由ci-host-map.json派生映射。audit-provenance.json绑定所有copy来源与生成文件；export_publication --ci-audits验证完整证明链即可导出，不传输密码。缺receipt、数据改动、外来run或未覆盖DB证据都阻断导出。本地仍可--secret-file扫描本次真实实验凭据。

aggregate从同一analysis生成可审阅publication artifact，不自动发布。根readme稳定，图/明细使用candidate source SHA + execution run ID + benchmark source/summary摘要的不可变runs目录与绝对URL；发布保留旧runs目录，使旧缓存readme仍能解析对应旧图。
