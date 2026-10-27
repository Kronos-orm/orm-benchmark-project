package com.kotlinorm.benchmark;

import com.alibaba.druid.pool.DruidDataSource;
import com.kotlinorm.BenchmarkExecutor;
import org.openjdk.jmh.annotations.*;
import java.util.concurrent.TimeUnit;

/** One operation is one transaction, not one row. Reset and verification are outside timing. */
@State(Scope.Thread)
@BenchmarkMode(Mode.SingleShotTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 10, batchSize = 1)
@Measurement(iterations = 30, batchSize = 1)
@Fork(value = 5, jvmArgsAppend = {"-Xms1g", "-Xmx1g", "-XX:+UseG1GC", "-Duser.timezone=UTC"})
@Threads(1)
public class InsertBenchmark {
    @Param({"Jdbc", "Kronos", "Jpa", "Jimmer", "Ktorm", "Mybatis"}) public String orm;
    @Param({"1", "100"}) public int transactionRows;
    private DruidDataSource pool;
    private BenchmarkExecutor executor;
    private int affected;

    @Setup(Level.Trial) public void setupTrial() throws Exception {
        try {
            pool = DataSourceHelper.openPool();
            FixtureSupport.createAndSeed(pool, 0);
            executor = DataSourceHelper.createExecutor(orm);
            executor.init(pool);
        } catch (Throwable failure) { close(); throw failure; }
    }

    @Setup(Level.Iteration) public void setupIteration() throws Exception {
        FixtureSupport.resetWrites(pool);
        executor.prepareInsert(FixtureSupport.rows(transactionRows));
        affected = -1;
    }

    @Benchmark public int insertTransaction() { return affected = executor.insertTransaction(); }

    @TearDown(Level.Iteration) public void verifyIteration() throws Exception {
        if (affected != transactionRows) throw new IllegalStateException("Unexpected affected count");
        FixtureSupport.requireCount(pool, transactionRows);
        JdbcExecutor jdbc = new JdbcExecutor(); jdbc.init(pool);
        var rows = jdbc.queryEntities(1, transactionRows);
        for (int i = 0; i < transactionRows; i++) FixtureSupport.requireRow(rows.get(i), i + 1);
        jdbc.close();
    }

    @TearDown(Level.Trial) public void close() throws Exception {
        try { if (executor != null) executor.close(); }
        finally { if (pool != null) pool.close(); }
    }
}
