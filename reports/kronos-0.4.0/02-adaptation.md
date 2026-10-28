# 任务二：候选接入与适配

状态：In Progress；CI已编译并执行真实数据库门禁，当前待MyBatis官方支持组合验证。

## 目标

将修复后 Kronos 0.4.0 接入可复现、公平且有正确性门禁的 JMH harness。

## 当前状态

当前选型已按2026-10-27官方release/Central核对，见versions/README.md；所有升级组合仍待编译/运行证明，主任务已提供候选仓库路径与源SHA，当前暂不消费暂存制品，等待最终候选和preflight放行。

## 已完成源码准备

- Kotlin2.4.21/Kronos0.4.0；KSP2.3.12、Jimmer0.12.4，仅保留KSP处理；Hibernate7.4.14.Final、Ktorm4.2.1、MyBatis-Plus3.5.18.1与官方声明core3.5.19。所有兼容性仍须编译/运行证明。
- `settings.gradle.kts`对Kronos插件marker与依赖使用独占candidate仓库，缺失路径立即报错；没有mavenLocal或Central回退。
- Java JMH1.37 annotation processor harness取代kotlinx-benchmark，移除报告绘图库/Faker对计时classpath的依赖。
- 六适配器共用17列、assigned Int主键；Kronos使用当前`KronosJdbcWrapper`、`Kronos.logging.enabled=false`与新结果终结API。
- `ReadBenchmark`返回完整List给JMH消费；统一有序id范围、返回1/100行、热区/均匀访问、两种表规模。
- `InsertBenchmark`使用SingleShotTime，每迭代仅一事务；计时外重置空表、生成新对象与逐字段回读校验。所有框架主场景均逐行INSERT、同一次commit，避免混入原生batch策略。
- SQL审计proxy只用于验证，主测量不安装proxy；门禁检查结果、类型证据、投影/谓词/绑定、JDBC execute数、commit数、连接关闭和生成键。
- 固定fixture为100字节VARBINARY(128)，明确DECIMAL(18,2)、DATETIME(3)，不使用框架LOB/JSON延迟路径。Map保留各框架原生返回类型；验证在计时外规范化java.sql.Date/Timestamp，并记录真实值类型。Jimmer Map仍包含显式entity→map转换，须披露。
- 隔离MySQL生命周期脚本拒绝未知datadir/端口，密码只在私有权限600文件及子进程环境；JFR复制JDK profile并关闭环境变量与系统属性事件。
- 分阶段runner记录候选/源码/runtime JAR hash、随机5-block顺序、完整argv与退出码、raw JSON和逐迭代导出CSV；门禁要求同一源码/制品/环境，以及有证据的pilot-review。
- 统计脚本仅读取formal measure目录，按独立fork均值推断，区分失败/未跑，输出区间/比值/独立PNG/SVG/PDF；profile数据不进入主成绩。

## 后续运行验证清单

- 将候选仓库限定到com.kotlinorm内容，用GradleexclusiveContent同时限定pluginManagement和dependencyResolution；记录解析出的所有Kronos坐标、POM/JAR SHA-256与源SHA。锁依赖并使用稳定依赖，避免SNAPSHOT fallback。
- 按候选公开Gradle用法接入。优先令非Kronos模块保留兼容的构建路径；如全局Kotlin升级导致Jimmer处理器不兼容，分别构建ORM适配器JAR并通过Java接口由同一JMH runner加载，确认运行时Kotlin stdlib兼容性。任何升级必须先固定版本并披露原因，按同一日期为所有竞争ORM核对当前稳定兼容版本，并保留相同功能定义。
- 删除重复KSP+kapt对同一Jimmer模型的双处理路径，只保留经过兼容性验证的一种，并核对生成输出。
- 以官方JMH runner为准，确定kotlinx-benchmark的最终生成配置是否完整支持Fork/SingleShotTime/JSON。如果不支持，切换显式JMH（可Java编写harness并依赖Kotlin适配器），固定JMH版本和生成器版本；报告绘图移到独立Python步骤，缩小计时classpath。
- 重写共同接口：queryEntity(id): Any、queryMap(id): Map、queryField(id): String、insertAssigned(...): affectedRows/可验证返回值、close()；提供校验专用normalizeEntity，不在计时内跑全字段断言或深hash。
- 加JDBC baseline，显式列名/相同绑定类型/完全物化；实体baseline为普通数据对象，Map baseline为相同键规范。不得只返回ResultSet或未消费stream。
- 新Kronos使用KronosJdbcWrapper与候选支持的select/where/toList等API；根据candidate真实源码核对，不照搬旧API。禁用日志、级联与非共同字段策略；候选compiler插件应在模型/DSL所在模块生效。
- 固定DDL（17列，明确DECIMAL scale、DATETIME精度、BLOB/字节语义、utf8mb4）；固定seed构造数据、预生成查询id序列和每轮写入对象。用户原配置改为专用环境注入并guard端口13307/数据库名，保留useServerPrepStmts=true。
- 共同pool预热完成；单线程primary pool固定1连接、validation/metrics关闭、统一autoCommit/isolation。prepared statement cache容量、serverPrepStmts/rewriteBatchedStatements统一显式记录；不强行关闭仅一方正常SQL计划缓存。
- SQL审计通过DataSource proxy在计时外捕获prepare SQL、绑定类型/值、execute/commit/rollback/生成键请求；模板和合成参数可公开。正式测量切换无代理池，校验报告与测量配置hash一致。
- 查询correctness检查所有列（ByteArray内容、BigDecimal数值与scale规范、时间精度），多id与缺失id按约定校验；insert检查精确rowcount和逐行内容，校验未变异的输入对象与唯一主键，失败则该场景不进入测量。

## 验收

六套（五ORM+JDBC）查询的SQL语义、投影、绑定类型、连接数/事务数、返回值完成度有证据。所有资源在finally关闭；异常不吞掉。独立MySQL之外的URL被明确拒绝。编译结果与candidate SHA/JAR hash有一一对应关系。

## 验证记录

已做Python AST、版本目录TOML和静态源码检查；Gradle/JVM编译与运行验证未做，等待修复候选及负载放行。API/处理器兼容尚未证明，不能把源码准备称为验证通过。
