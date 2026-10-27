# 任务一：公平性缺陷审计

状态：Done（只读源码证据）；运行时影响尚未验证。

## 目标

识别原测试可能测到的实际工作与宣称指标之间的偏差，作为重构依据。不能把源码缺陷直接换算成性能损失。

## 代码事实与影响

1. `BenchmarkExecutor.kt:16,21,26` 查询方法返回 Unit，四个 benchmark 也返回 Unit。实体/Map/字段值被丢弃。JDBC 有可观察副作用，不等于整条查询一定被 JIT 删除，但物化/转换工作缺少可靠消费，正确性也无法由调用方验证。应返回真实值交由 JMH 消费。
2. 所有查询只查 `id=1`。`count=100000` 是表规模，不是每次返回行数或随机访问范围；属于热主键单行场景。
3. `InsertBenchmark.kt:26,40` 每次插入 10000 行，报告器统一写 Operations/s；没有说明一 op 等于一批，不能当作 rows/s。接口注释还声称 single row。
4. 插入只在 trial 最后 truncate，warmup 与 measurement 期间表一直增长。数据规模、页分裂、缓存、redo/检查点和磁盘负荷随调用次数漂移，各 ORM 插入更快会造成更大表。
5. Hibernate 使用 IDENTITY 并循环 persist，MyBatis 使用 BATCH 且提交，Ktorm/Kronos/Jimmer 走不同批量 API。Jimmer默认10000、Hibernate设1000；是否一次事务/生成键/驱动rewrite未统一，必须实际捕获，不可直接宣称同一种批量。
6. Hibernate 每次 fresh Session；MyBatis fresh SqlSession。Hibernate显式关闭查询计划缓存，其他 ORM 没有对应控制；会把不对称配置当作 ORM 性能。
7. Jimmer Map 路径先完整 entity 再手工 map；MyBatis 标量路径先生成部分 entity 再取 name。Ktorm map key使用列名，Jimmer/JPA使用属性名。原生 Map/标量支持范围不同，需要规范返回契约并在结果中标出转换路径。
8. 每个场景通过 Kronos `sync`、全局 executor 建表/灌数据；使用被测 ORM 作为所有竞品 fixture，DDL与类型假设耦合。初始化只往表插数据，没有先独立断言 rowcount/首行/空表。
9. MyBatis prepareData 将 updateTime 取自 createTime，与其他适配器不一致。MyBatis id 为 Long，其余为 Int；其 IdType.INPUT 与其他 IDENTITY 模型也不同。
10. Jimmer comment 使用 Serialized 与自定义 ByteArrayScalarProvider；必须验证实际列类型与往返字节，不假设等价。
11. Faker 无固定 seed，数据包含随机过去时间；各 fork 数据不同，BigDecimal scale、时区/时间精度也未定义。
12. 仅 `@Fork(1)`；warmup 只有次数未显式时长。没有外部重复/顺序随机化/环境清单/原始 fork 数据解释。
13. pool lazy singleton未显式关闭；globalExecutor与sync产生的wrapper未统一生命周期。onDestroy混合TRUNCATE与资源关闭，失败可能污染下一轮。
14. 依赖Kronos `0.0.3-SNAPSHOT`、Kotlin2.1.0，使用 `KronosBasicWrapper`、LastInsertIdPlugin、旧queryOne/queryMap与旧DSL，不能据此评测新版0.4.0。
15. 原报告器固定标题单位ops/s、按点估计降序排名、图片指向远程result分支；未保留方法适用范围或SQL证据。主项目引入dataframe/kandy等报告依赖，也会扩大测量classpath。

## 验收

已读取五套executor、四个benchmark、所有模型、版本目录、构建配置和报告器；没有执行测试或读取数据库。后续每项结论必须由SQL审计或正确性检查进一步验证。

## 方法来源

[JMH DeadCode 官方样例](https://github.com/openjdk/jmh/blob/master/jmh-samples/src/main/java/org/openjdk/jmh/samples/JMHSample_08_DeadCode.java)说明返回结果由JMH隐式消费；[PerInvokeSetup 官方样例](https://github.com/openjdk/jmh/blob/master/jmh-samples/src/main/java/org/openjdk/jmh/samples/JMHSample_38_PerInvokeSetup.java)说明逐调用setup会带来计时与状态干扰。此处没有据此声称当前DB调用整体已被消除。
