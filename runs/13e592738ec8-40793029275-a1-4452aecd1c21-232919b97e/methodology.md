# Measurement method

- Each scenario uses five independent JVM forks/blocks. All six adapters within a block share one runner VM and dedicated MySQL, in a fixed-seed randomized order.

- Queries fully materialize their result and include connection/session lifetime. Tables contain 1,000 / 100,000 rows; queries return 1 / 100 rows across entity / map / scalar and hot / uniform access.

- Writes time the first row-wise INSERT transaction on a reset empty table, including execution and COMMIT. TRUNCATE, object preparation and result checks occur outside timing.

- All measurement values are averaged within each fork. Five fork means determine the mean and Student t 95% interval; all samples and failure states remain available.

- Paired ratios are other latency / Kronos latency, using matching-block log-ratios and 95% intervals. The table n is the independent fork count.

- Environment evidence records the JDK, database image, driver, pool and caches. Separate correctness checks verify SQL, materialized values and resource lifetime.

- Reads: 5 × 2s warmup, 10 × 2s measurement; µs/query.

- Writes: 2000 warmup transactions, 300 SingleShot measurements, batch size = 1; µs/transaction.

# 测量方法

- 每个场景有五个独立 JVM fork/block；同一 block 的六个适配器在同一 runner VM 和独立 MySQL 中按固定 seed 随机顺序执行。

- 查询返回完整物化的结果，计入连接/会话生命周期。表规模为 1,000 / 100,000 行，返回量为 1 / 100 行，覆盖 entity / map / scalar 与 hot / uniform 访问。

- 写入测量的是空表首个逐行 INSERT 事务，包含执行和 COMMIT。TRUNCATE、对象准备和结果校验在计时外。

- 先对每个 fork 的全部 measurement 值取均值，再用五个 fork 均值计算均值和 Student t 95% 区间；保留所有样本及失败状态。

- 配对比值为其他框架时延 / Kronos 时延，使用相同 block 的 log-ratio 和 95% 区间。表中的 n 表示独立 fork 数。

- JDK、数据库镜像、JDBC 驱动、连接池和缓存配置随环境证据保存；SQL、结果内容与资源生命周期通过独立正确性校验。

- 读取：5 × 2s 预热，10 × 2s 测量；单位为 µs/query。

- 写入：2000 次事务预热，300 次 SingleShot 测量，batch size = 1；单位为 µs/transaction。
