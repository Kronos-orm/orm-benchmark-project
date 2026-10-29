# ORM benchmark

JMH comparisons of Kronos, Hibernate, Jimmer, Ktorm, MyBatis-Plus and typed JDBC on MySQL.

[Performance report](https://github.com/Kronos-orm/orm-benchmark-project/blob/result/readme.md) · [CI](https://github.com/Kronos-orm/orm-benchmark-project/actions)

## Run

`config/formal.json` fixes runtime identity, workload schedule and measurement parameters. The formal workflow reuses its original sealed runtime; consumers do not compile JVM code. `libs.versions.toml` defines dependency versions and `config/mysql.json` pins the database image for new runtime production.

Dispatch `measure-sealed.yml` on `main` with the exact `expected_controller_sha` and SHA-256 of `config/formal.json` as `expected_protocol_sha`.

The matrix has 26 scenarios × 6 adapters × 5 independent blocks, split across 40 jobs with at most 8 concurrent jobs. Each case/block runs all adapters on one runner VM and database in randomized order. All iteration values are averaged within a fork before the five fork means enter inference.

CI validates SQL and results, retains raw JSON/CSV and commands, verifies real-credential audit receipts and the shared execution context, then automatically updates the report only after all 780 cells pass. Existing versioned evidence remains available.

## 测量与报告

协议记录在 `config/formal.json`。读取覆盖两种表规模、返回行数、投影和访问分布；写入计入逐行 INSERT 与 COMMIT，TRUNCATE、数据准备和校验在计时外。JDBC、驱动、连接池和数据库配置统一。

报告由同一份统计数据生成 Markdown、图表和可下载证据。首页保留三个预先指定的关键场景，完整中英文结果按需打开；五个 block 的均值和区间保留全部样本。
