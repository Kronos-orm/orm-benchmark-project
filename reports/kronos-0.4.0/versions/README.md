# 依赖版本与兼容性核对

核对截止：2026-10-27。状态：已使用candidate7（d71132478b7282202d375d6579bd943331fa4fd3）完成受限临时API编译；未启DB、未执行正确性/pilot/性能。最终候选须替换重建。本地编译记录保留于仓库外私有工作记录；正式CI将保留candidate/runtime/source摘要与完整artifact。

## 取证规则

逐个读取Maven Central官方metadata和精确版本POM，再核对项目官方GitHub release的发布日期、tag和prerelease标记。保存的[Central摘要](upstream/central-summary.json)、[POM摘要](upstream/pom-summary.json)、[release摘要](upstream/release-summary.json)及各原始XML/POM用于复核；[快照摘要清单](upstream/snapshot-files.json)记录文件SHA-256；兼容性源码摘要另见[兼容API记录](upstream/compatibility-source-audit.json)。

`versioning.release`不能直接当作稳定版：Hibernate该字段指向8.0.0.Beta3，官方7.4页标注latest stable，故选择7.4.14.Final。搜索引擎缓存显示的旧版本未用作最终依据。

[机器可读选型](selected-versions.json)区分已发布版本与尚待验证的组合；正式构建必须进一步保存解析版本和JAR hash，不能仅凭此文声称可运行。

## 计划固定的ORM

- **Hibernate ORM 7.4.14.Final**，2026-10-25发布。[官方稳定系列](https://hibernate.org/orm/releases/7.4/)、[官方release](https://github.com/hibernate/hibernate-orm/releases/tag/7.4.14)、[Central POM](https://repo.maven.apache.org/maven2/org/hibernate/orm/hibernate-core/7.4.14.Final/hibernate-core-7.4.14.Final.pom)。使用其Jakarta Persistence3.2.0；MySQLDialect7.4.14源码最低版本为8，JDK21与本机MySQL8.0.22仍须经实际门禁证明。
- **Jimmer 0.12.4**，2026-10-06发布。core/sql-kotlin/ksp均统一0.12.4。[官方release](https://github.com/babyfish-ct/jimmer/releases/tag/v0.12.4)、[Central POM](https://repo.maven.apache.org/maven2/org/babyfish/jimmer/jimmer-sql-kotlin/0.12.4/jimmer-sql-kotlin-0.12.4.pom)。原先0.9.72不再作为默认对照。
- **Ktorm 4.2.1**，2026-06-20发布。[官方release](https://github.com/kotlin-orm/ktorm/releases/tag/v4.2.1)、[Central POM](https://repo.maven.apache.org/maven2/org/ktorm/ktorm-core/4.2.1/ktorm-core-4.2.1.pom)。本实验仅用core DSL/entity绑定，不引入Ktorm KSP插件。
- **MyBatis-Plus 3.5.18**，2026-10-25发布，同时显式计划使用**MyBatis core 3.6.0**，后者2026-10-23发布。[Plus release](https://github.com/baomidou/mybatis-plus/releases/tag/v3.5.18)、[core release](https://github.com/mybatis/mybatis-3/releases/tag/mybatis-3.6.0)。Plus当前[POM](https://repo.maven.apache.org/maven2/com/baomidou/mybatis-plus/3.5.18/mybatis-plus-3.5.18.pom)仍声明core3.5.19，因此3.6.0组合是待编译/运行证明的升级目标，不是已证实兼容。若不兼容，必须保留具体错误证据，说明是否选用Plus官方声明组合，不可静默降级或将Plus换成原生MyBatis再沿用原标签。使用MybatisSqlSessionFactoryBuilder完成Plus初始化；JavaTime handler已内置core，移除重复的旧jsr310扩展JAR。
- **Kronos 0.4.0**使用主任务随后批准的精确候选仓库/SHA，不能与上述已发布稳定版本混淆；所有框架仍有相同功能与正确性门禁。

## 共同基础设施

六适配器共享**Connector/J9.7.0**与**Alibaba Druid1.2.28**。驱动9.7.0于2026-04-22发布，[官方说明支持MySQL8.0及以上](https://dev.mysql.com/doc/relnotes/connector-j/en/news-9-7-0.html)。当前全线最新GA是26.10.0（2026-10-21），但[官方说明要求MySQL8.4及以上](https://dev.mysql.com/doc/relnotes/connector-j/en/news-26-10-0.html)，26.7同样要求8.4。因此本机现有独立8.0.22环境采用9.7.0，不为追版本更改服务器安装，也不声称26.10官方支持8.0。选型对所有框架相同。

[Druid1.2.28官方release](https://github.com/alibaba/druid/releases/tag/1.2.28)日期2026-03-10；此处为Alibaba连接池。JMH core/generator均固定1.37，Central metadata没有更高稳定版。Jackson限定当前com.fasterxml坐标2.x线的2.22.4，仅用于计时外验证/报告JSON；不称作Jackson所有主线的总体最新版本。

JDK统一使用已安装21.0.10并明确记录完整供应商/构建信息；它是实验固定工具链，未宣称为截至日期最新JDK。正式测量记录硬件、MySQL变量、AC/电池、节能配置、热状态及空闲CPU基线；只采集状态，不主动终止用户IDE/网站等进程。

## Kotlin2.4.21 / Jimmer / KSP2

Kotlin编译器统一2.4.21，Kotlin BOM和reflect2.4.21统一运行时；实际解析图仍待构建确认。KSP固定当前稳定**2.3.12**（2026-09-09），仅使用KSP2，移除kapt双处理。

[Jimmer0.12.4处理器POM](https://repo.maven.apache.org/maven2/org/babyfish/jimmer/jimmer-ksp/0.12.4/jimmer-ksp-0.12.4.pom)编译目标API为2.1.20-2.0.0。处理器入口源码使用公共SymbolProcessorProvider/SymbolProcessor/Resolver SPI；其源码身份存于[API摘要](upstream/api-source-summary.json)与[源码hash](upstream/source-audit-hashes.json)。[KSP2.3.0官方说明](https://github.com/google/ksp/releases/tag/2.3.0)指出其版本已与Kotlin编译器解耦；[2.3.12说明](https://github.com/google/ksp/releases/tag/2.3.12)以显式opt-in保护旧处理器的backing-field行为。本模型使用抽象interface属性，无显式backing field或field-use-site迁移；未开启新特性opt-in。处理器classpath显式选择API2.3.12，避免保留两个目标API版本。

以上支持源码层的兼容推断，不代替编译验证。放行后先运行Jimmer KSP/适配器窄编译，再检查生成实体/Draft是否完整、SQL结果是否一致。遇到问题先依据错误定位，不降低Kronos编译器版本、不更换查询/写入语义、不把失败场景计入成绩。

Jimmer当前仍支持单实体save(INSERT_ONLY)。适配器用单实体入口执行每行INSERT，消除先包成单元素Iterable再走batch facade的多余工作，保持17列、assigned key、每行一次INSERT、外部一次事务。其新createInsert为typed-source DML，未据此改变本实验的实体输入语义。
