# 验证记录

更新：2026-10-27

## 准备阶段

- 已确认benchmark cwd、git HEAD/分支/remote与git status；起点只有用户DataSourceHelper改动和未跟踪.DS_Store。
- 对benchmark及祖先检查AGENTS.md：未发现。
- 已将DataSourceHelper原文件复制到Git外private路径，确认目录700/文件600；内容未输出，之后仅读取字符串脱敏结构，未打印完整文件或diff。
- 已读四benchmark、共同接口、五ORMexecutor与所有模型、Gradle文件/版本目录、报告生成器。
- 使用`sw_vers`、`uname -m`、`sysctl`、`/usr/libexec/java_home -V`、`/usr/local/mysql/bin/mysqld --version`记录轻量环境初查。最后一条只查询binary版本，没有启动服务器。
- 已参考Kronos开发/使用指南、vibecoding-tasklist与canvas技能；已读取JMH官方DeadCode、PerInvokeSetup示例以及benchmark远程首页。远程结果未替代本地HEAD证据。
- 已建立本任务文档，不修改任何Kotlin/Gradle或主仓文件。
- 未运行任何Gradle、MySQL初始化/启动/查询、编译、JMH或性能测量。准备结果不构成性能报告。

## 第二阶段：仅源码准备

- 主任务允许独立benchmark源码适配，但禁止Gradle、DB、JMH/JFR/GC负载；整个阶段遵守此限制。
- 改写Gradle/Kotlin版本与候选exclusive仓库；保留竞品运行库固定版本，KSP切换到官方Kotlin文档的2.3.10并移除kapt双处理。参考：https://kotlinlang.org/docs/ksp-quickstart.html 。
- 读取当前主仓API源码核对KronosJdbcWrapper、Kronos.logging.enabled、select终结、事务与insert结果；未修改主仓。
- 新增6适配器结果接口、确定性17列fixture、JDBC基线、Java JMH读写harness、计时外SQL/全字段/生命周期门禁。
- 新增manage_mysql.py、run_experiment.py、analyze_results.py；仅写入，未执行其stage或数据库动作。
- 通过`/usr/local/bin/python3.13`的`ast.parse`与`tomllib.loads`静态解析三个Python脚本及版本目录。最初系统Python缺少tomllib，改用已安装3.13完成；没有安装依赖。
- 参考官方JMH1.37 JFR profiler源码确认`configName`支持配置文件路径；脚本生成禁环境变量/系统属性事件的JFC，以免诊断泄密。
- 原用户配置的私有备份保持完整；原.DS_Store保留在磁盘，本地忽略；公开源码使用固定专属13307端点和私有环境密码。
- 所有编译、运行、正确性、SQL、性能、JFR、GC验证依然未运行。状态必须保持未测量。

- 最终轻量检查：31个Java/Kotlin/Gradle文件的字符串/注释/括号静态扫描、三个Python脚本AST、版本目录TOML、文档相对链接均通过。此检查不是编译器验证。
- 对公开改动扫描原配置密码，未发现匹配；仅输出检查结果，没有输出密码。确认原.DS_Store仍在磁盘。

## 第三阶段：稳定版本与兼容性轻量核对

- 截至2026-10-27，直接访问Central metadata/POM与官方GitHub release API，确认Hibernate7.4.14.Final、Jimmer0.12.4、Ktorm4.2.1、Plus3.5.18、MyBatis3.6.0、Druid1.2.28、KSP2.3.12、JMH1.37；证据留于versions/upstream。
- 更新版本目录与构建配置；所有ORM维持相同查询/事务语义。MyBatis core3.6.0组合尚需证明，与Plus声明3.5.19的差异已显式记录。
- 官方驱动说明：26.7/26.10要求MySQL8.4+，9.7.0支持8.0+；现有独立8.0.22环境六方统一9.7.0。
- Jimmer处理器公共SPI与KSP2独立版本/opt-in规则已源码审查；不将源码推断称作编译通过。单实体INSERT_ONLY入口避免多余batch facade，SQL/结果门禁不变。
- runner只增加正式运行前AC/节能/热状态/空闲CPU证据采集命令定义；没有实际执行这些命令，也不终止用户IDE/网站。
- 本阶段没有读取原私密配置/备份，没有构建、启动数据库、运行pilot/测量或profile。候选精确SHA仍未确定。

- 额外验证JMH core/generator1.37、Jackson Kotlin2.22.4、KSP plugin marker2.3.12的精确POM可取得；静态AST/TOML/文档链接检查通过。
- 主任务将后续负载拆为构建/正确性/pilot与空闲主机正式测量两阶段；runner已分别要求BENCH_ALLOW_LOAD与额外BENCH_ALLOW_MEASUREMENT，当前均未启用。标志仅防误触，不替代明确放行。

## 第四阶段：呈现与解释准备

- 收到主任务候选源SHA d71132478b7282202d375d6579bd943331fa4fd3及jvm-repository-7路径；候选仍在构建，未读取/消费其制品，未启动任何负载。
- 编写统计解释、报告结构与证据链文档；创建方法canvas，只展示真实源码/版本/协议事实，不包含成绩占位图或模拟跑分。
- preflight与正式测量仍分开等待；远程CI状态由主任务跟踪，本agent不并行启动本地重编译。

- 呈现源码新增完整case定义、操作单位、planned/PASS/FAIL/NOT_RUN覆盖计数，以及执行时raw/log/CSV摘要和分析时raw一致性检查；当前没有运行分析。
- 方法canvas的SDK导出与视觉约束已静态核对；此环境未提供TypeScript parser，宿主渲染/类型检查尚未核验，留待实际打开后检查。
- 统计图源码将标注每组实际fork n；折算操作率/行率按每fork计算并明确为时延折算，不新增独立吞吐成绩。

## 第五阶段：官网嵌入链路与报告发布准备

- 只读核对benchmark远程main c8cfb23a4e2478def2feb8d579d81b9782d77aa7、result 70b18e4d280511e292a5ca15463142736a04e905及GitHub repo/pages元数据。官网当前为ngx-markdown加载result/readme.md，原图片为绝对raw URL；无benchmark iframe/postMessage/JSON消费，Pages未启用。
- 只读核对主仓BenchmarkComponent、两语言resources/benchmark页、路由/hash/base、静态demo转换和站点合并。未修改主仓docs。
- 准备result/readme.md兼容导出、静态Web/JSON界面、版本化raw/source/analysis/figure目录、实际实验凭据扫描、ZIP与文件摘要及raw到展示均值验证。
- 发布workflow仅手动接收已复核publication的精确commit，校验后部署result且保留既有版本目录；未执行workflow、push或部署。
- 绝对Markdown URL/子路径资源解析、Python AST、JS语法检查通过；未实测，未导出新成绩，未覆盖线上旧结果。

- 根readme呈现收敛为简洁中英双语摘要，最多3张测量前注册关键图；完整26类场景/156个框架组合、中文/英文详细Markdown和raw按需打开，不全量预载所有图。
- publication_markdown.py、HTML/JSON共用同一analysis/report对象；根JSON缩为索引，case明细按需加载。validator增加raw到均值/median/CI及根关键图集合的交叉检查。

- 额外静态验证：Ruby标准YAML解析通过；确认workflow只有workflow_dispatch、精确SHA输入、result发布且clean=false。未调度实际workflow。
- 导出器使用固定输入时间与属性生成可重复ZIP；validator检查原始block状态、统计显示与固定关键场景，并在发布工作流锁定官网raw基址。完整数据验证仍未执行。

## 第六阶段：API适配与CI迁移（2026-10-27）

- 临时candidate7受限API编译通过，所有五ORM、JDBC/JMH及KSP生成源码完成编译；运行正确性尚未验证。本地构建日志/命令/transport预检记录保留在仓库外，正式可复现证据由CI candidate/runtime/source artifacts提供。
- 新CI DAG resolve→producer一次→validate/pilot→8组×5blocks→alwaysaggregate。PR→main只build；DB入口要求手动指定validate/pilot/measure；正式measure另需批准40SHA/release phrase/匹配pilot review。
- 4个轻量合同测试通过：780唯一单元、40job无额外fork、seal变更/新增/缺失/symlink拒绝、全缺失时保留780 NOT_RUN且不产生数值。Python AST、YAML和diff检查通过。CI未触发；未测量/部署。

- 首轮PR CI resolve与4项合同测试通过；producer在setup-java精确selector处失败，Adoptium API返回21.0.10+7.0.LTS而非21.0.10+7。修正selector，仍保持相同JDK实际build；DB相关job均skipped。

- [build-only numeric dispatch](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40528058784)已成功：resolve/producer全绿，Kronos JVM candidate一次构建、全部适配器/JMH编译、candidate SHA强校验、完整bundle seal和artifact上传通过；DB相关job均skipped。numeric workflow ID398381230支持feature ref，无需修改默认result分支。
- 新增正式measure复用pilot原始bundle，校验Kronos/benchmark源码身份、原producer run、seal与48个pilot PASS/raw摘要；本地5项轻量合同测试通过。artifact复用、MySQL正确性、pilot和measure分支尚未运行，等待最终候选/对应阶段放行。

## CI真实凭据证明链与最终候选pilot准备（2026-10-28）

- 新增DB job原地真实secret扫描与逐文件hash-bound receipt；扫描失败阻断所有待上传raw。aggregate/export验证来源、run/block/cell与精确字节，无需上传密码或提供dummy文件。8项合同测试通过。
- 移除任意release phrase与人工ACCEPTED条件；pilot自动保留实际warmup/iteration统计、raw摘要与正确性marker，正式measure复用原bundle。
- 主任务曾条件放行532e8372f1059ae50f62f171dcc4cf2e69fdb685一次CI pilot，触发前因Native metadata修复将改变SHA而暂缓。当前只build-only复验；待新SHA后同run构建→正确性→pilot，不单独validate、不运行正式矩阵或发布。

## Provisional pilot与immutable consumer修复（2026-10-28）

- [6878 provisional pilot](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40608167300)完成producer，首个consumer seal校验失败；DB启动/validate/48pilot均未执行，没有性能数字。主仓同SHA覆盖率需补测，故此源不能用于最终formal bundle。
- 真实Python子进程合同复现：consumer导入模块新建__pycache__，改变sealed文件集。修复为workflow全局PYTHONDONTWRITEBYTECODE、-B消费者命令与独立入口sys.dont_write_bytecode；不排除新文件、不放宽seal。13项合同通过，包含verify和validate前导读取后全文件集/hash不变，且无DB访问。
- producer上传前从真实bundle入口再校验，runtime artifact明确保留全部sealed文件。正常更新PR构建验证；不对6878重复pilot，等待主任务新源SHA。

## 真实DB配置失败与只读诊断（2026-10-28）

- [f49 pilot](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40611024823)首次通过immutable consumer并启动独立MySQL，但共同Druid池在ORM校验前失败；48试跑未执行，真实secret扫描通过后保留了19KB preflight artifact。
- [只读diagnose](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40612227523)按精确artifact ID/ZIP digest下载、核验receipt后，定位实际IllegalArgumentException：timeBetweenEvictionRunsMillis must > 0。统一改为正数24h，所有六适配器一致、testWhileIdle=false，并记录实际pool policy；producer新增不连接DB的真实Druid setter contract。
- 正常audit成功后直接从同一hash-bound证据发简洁安全failure annotation/step summary；未审计内容不输出，以后不必重复dispatch诊断桥。
- 当前主仓source仍可能因IDE测试修复改变；按主任务安排下一步只对f49做validate-only适配，不运行48pilot或formal，validate bundle不能用作pilot复用。

## SQL紧凑表示的共同规范化（2026-10-28）

- [f49 validate-only](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40613160401)已通过Jdbc/Kronos前序检查，JPA在SQL形状核对失败；audit后安全annotation保留实际同17列/range/order SQL，仅操作符两侧没有空白。
- 改为共同SQL token规范化：保留字符串字面量与参数边界，只统一token间空白/简单标识符qualifier/谓词分组。producer无DB契约输入采用这条真实compact SQL及spaced形式；>=改>、AND改OR、order DESC、缺参数、quoted问号和named参数均必须拒绝。未增加Hibernate特判、未放宽列集合/绑定值/连接事务检查。

## MyBatis声明兼容组合（2026-10-28）

- validate40634312963在前五adapter通过后，MyBatisPlus3.5.18+强制core3.6.0实际NoSuchMethodError(findForClass)。最新Plus3.5.18.1直接Central可解析，仍声明core3.5.19，现采用该官方组合；保留错误和POM依据，不记录失败性能分数。

- 正式矩阵max-parallel由4提高为8；40 jobs/780 cells/5独立blocks不变，六adapter仍在各自同一VM与独立DB内随机排序。未发现需限制为4的科学约束；账户配额/host分配待实际run记录，预计读取净下限48分钟并非实测完成时间。

- 本机GitHub artifact存储TLS EOF仍可重现；runner下载校验正常。补充scan receipt/全部字节hash校验后的真实pilot成功diagnostics notice，包含原review及receipt/review摘要，供API即时审阅warmup/CV而不改变计时。新增合同拒绝scan后review变更且不打印任何内容；15合同通过。

- validate-only40636419426（Kronos f49、benchmark8bd）完整六adapter门禁PASS，Plus3.5.18.1/core3.5.19已实际验证。正式aggregate在完整receipt派生链验证后按原8group发API可读同源summary：fork means/均值CI/paired ratios/raw及receipt hash/来源与host证据；没有第二套计算或改计时。变更summary即拒绝输出合同及全部16合同通过。
