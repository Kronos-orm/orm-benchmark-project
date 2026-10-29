package com.kotlinorm.benchmark;

import com.alibaba.druid.pool.DruidDataSource;
import com.kotlinorm.BenchmarkExecutor;
import com.kotlinorm.jimmerBenchmark.JimmerBenchmark;
import com.kotlinorm.jpaBenchmark.JpaExecutor;
import com.kotlinorm.kronosBenchmark.KronosExecutor;
import com.kolinorm.ktormBenchmark.KtromExecutor;
import com.kotlinorm.mybatisBenchmark.MybatisExecutor;

/** Fixed local endpoint: no route to a user's existing database is accepted. */
public final class DataSourceHelper {
    public static final String DATABASE = "orm_benchmark_040";
    public static final int PORT = 13307;
    public static final long HOUSEKEEPING_INTERVAL_MILLIS = java.util.concurrent.TimeUnit.DAYS.toMillis(1);
    public static final String URL = "jdbc:mysql://127.0.0.1:13307/" + DATABASE
        + "?useSSL=false&allowPublicKeyRetrieval=true&useServerPrepStmts=true"
        + "&cachePrepStmts=true&prepStmtCacheSize=256&prepStmtCacheSqlLimit=2048"
        + "&rewriteBatchedStatements=false&connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true";
    private DataSourceHelper() {}

    public static DruidDataSource openPool() throws Exception {
        String password = System.getenv("BENCH_DB_PASSWORD");
        if (password == null || password.isBlank()) throw new IllegalStateException("BENCH_DB_PASSWORD is required; its value must remain private");
        DruidDataSource pool = uninitializedPool();
        try {
            pool.setPassword(password);
            pool.init();
            try (var connection = pool.getConnection()) {
                if (!connection.getCatalog().equals(DATABASE)) throw new IllegalStateException("Unexpected catalog");
                String jdbcUrl = connection.getMetaData().getURL();
                if (!jdbcUrl.startsWith("jdbc:mysql://127.0.0.1:13307/" + DATABASE + "?")) throw new IllegalStateException("Endpoint guard rejected connection");
            }
            return pool;
        } catch (Throwable failure) {
            pool.close();
            throw failure;
        }
    }

    /** Shared by every adapter; validates setter compatibility without secrets, init or connections. */
    static DruidDataSource uninitializedPool() {
        DruidDataSource pool = new DruidDataSource();
        pool.setUrl(URL);
        pool.setUsername("orm_benchmark");
        pool.setDriverClassName("com.mysql.cj.jdbc.Driver");
        pool.setInitialSize(1); pool.setMinIdle(1); pool.setMaxActive(1);
        pool.setMaxWait(30_000);
        pool.setDefaultAutoCommit(true);
        pool.setDefaultTransactionIsolation(java.sql.Connection.TRANSACTION_READ_COMMITTED);
        pool.setTestOnBorrow(false); pool.setTestOnReturn(false); pool.setTestWhileIdle(false);
        pool.setPoolPreparedStatements(false);
        // Druid1.2.28 rejects nonpositive intervals; keep housekeeping outside every short-lived fork.
        pool.setTimeBetweenEvictionRunsMillis(HOUSEKEEPING_INTERVAL_MILLIS);
        return pool;
    }

    public static BenchmarkExecutor createExecutor(String name) {
        return switch (name) {
            case "Jdbc" -> new JdbcExecutor();
            case "Kronos" -> new KronosExecutor();
            case "Jpa" -> new JpaExecutor();
            case "Jimmer" -> new JimmerBenchmark();
            case "Ktorm" -> new KtromExecutor();
            case "Mybatis" -> new MybatisExecutor();
            default -> throw new IllegalArgumentException("Unknown ORM: " + name);
        };
    }
}
