package com.kotlinorm.benchmark;

import com.alibaba.druid.pool.DruidDataSource;
import com.kotlinorm.BenchmarkExecutor;
import org.openjdk.jmh.annotations.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 2)
@Measurement(iterations = 10, time = 2)
@Fork(value = 5, jvmArgsAppend = {"-Xms1g", "-Xmx1g", "-XX:+UseG1GC", "-Duser.timezone=UTC"})
@Threads(1)
public class ReadBenchmark {
    @Param({"Jdbc", "Kronos", "Jpa", "Jimmer", "Ktorm", "Mybatis"}) public String orm;
    @Param({"entity", "map", "scalar"}) public String projection;
    @Param({"1000", "100000"}) public int tableRows;
    @Param({"1", "100"}) public int resultRows;
    @Param({"hot", "uniform"}) public String access;
    private DruidDataSource pool;
    private BenchmarkExecutor executor;
    private int[] ids;
    private int cursor;

    @Setup(Level.Trial) public void setup() throws Exception {
        try {
            pool = DataSourceHelper.openPool();
            FixtureSupport.createAndSeed(pool, tableRows);
            executor = DataSourceHelper.createExecutor(orm);
            executor.init(pool);
            ids = new int[65536];
            Random random = new Random(FixtureSupport.SEED);
            for (int i = 0; i < ids.length; i++) ids[i] = access.equals("hot") ? 1 : 1 + random.nextInt(tableRows - resultRows + 1);
            var entities = executor.queryEntities(1, resultRows);
            if (entities.size() != resultRows) throw new IllegalStateException("Incomplete materialization");
            for (int i = 0; i < entities.size(); i++) FixtureSupport.requireRow(entities.get(i), i + 1);
        } catch (Throwable failure) { close(); throw failure; }
    }

    @Benchmark public Object query() {
        int id = ids[cursor++ & (ids.length - 1)];
        return switch (projection) {
            case "entity" -> executor.queryEntities(id, resultRows);
            case "map" -> executor.queryMaps(id, resultRows);
            case "scalar" -> executor.queryNames(id, resultRows);
            default -> throw new IllegalStateException("Unknown projection");
        };
    }

    @TearDown(Level.Trial) public void close() throws Exception {
        try { if (executor != null) executor.close(); }
        finally { if (pool != null) pool.close(); }
    }
}
