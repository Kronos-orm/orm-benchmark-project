package com.kotlinorm.benchmark;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.alibaba.druid.pool.DruidDataSource;
import com.kotlinorm.BenchmarkExecutor;
import java.nio.file.*;
import java.sql.*;
import java.util.*;

/** Fails the entire gate if any adapter disagrees on values, SQL, transactions or resources. */
public final class ValidateBenchmark {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final List<String> ORMS = List.of("Jdbc", "Kronos", "Jpa", "Jimmer", "Ktorm", "Mybatis");

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Usage: ValidateBenchmark <output-directory>");
        Path directory = Path.of(args[0]); Files.createDirectories(directory);
        Map<String, Object> summary = new LinkedHashMap<>();
        Files.deleteIfExists(directory.resolve("PASS.json"));
        try (DruidDataSource pool = DataSourceHelper.openPool()) {
            FixtureSupport.createAndSeed(pool, 1000);
            write(directory.resolve("environment.json"), environment(pool));
            for (String orm : ORMS) {
                SqlAudit audit = new SqlAudit(pool);
                try (BenchmarkExecutor executor = DataSourceHelper.createExecutor(orm)) {
                    executor.init(audit);
                    Map<String, Object> result = new LinkedHashMap<>();
                    for (int count : new int[]{1, 100}) for (int first : new int[]{1, 901}) {
                        for (String projection : List.of("entity", "map", "scalar")) {
                            audit.reset();
                            List<?> values = query(executor, projection, first, count);
                            if (values.size() != count) throw new IllegalStateException("Result count mismatch");
                            for (int i = 0; i < count; i++) {
                                if (projection.equals("scalar")) {
                                    if (!FixtureSupport.row(first + i).getName().equals(values.get(i))) throw new IllegalStateException("Scalar mismatch");
                                } else FixtureSupport.requireRow(values.get(i), first + i);
                            }
                            List<Map<String, Object>> events = audit.snapshot();
                            checkQuery(events, projection, first, count);
                            if (audit.liveConnections() != 0) throw new IllegalStateException("Query connection leak");
                            Map<String, String> valueTypes = new TreeMap<>();
                            if (projection.equals("scalar")) valueTypes.put("name", values.getFirst().getClass().getName());
                            else for (var field : FixtureSupport.normalize(values.getFirst()).entrySet()) {
                                valueTypes.put(field.getKey(), field.getValue() == null ? "null" : field.getValue().getClass().getName());
                            }
                            result.put(projection + "-first" + first + "-rows" + count, Map.of("events", events, "resultValueTypes", valueTypes));
                        }
                    }
                    for (String projection : List.of("entity", "map", "scalar")) {
                        audit.reset();
                        if (!query(executor, projection, 1001, 1).isEmpty()) throw new IllegalStateException("Missing-row mismatch");
                        checkQuery(audit.snapshot(), projection, 1001, 1);
                        result.put(projection + "-missing", audit.snapshot());
                    }
                    for (int count : new int[]{1, 100}) {
                        FixtureSupport.resetWrites(pool);
                        executor.prepareInsert(FixtureSupport.rows(count));
                        audit.reset();
                        if (executor.insertTransaction() != count) throw new IllegalStateException("Affected-row mismatch");
                        List<Map<String, Object>> events = audit.snapshot();
                        checkWrite(events, count);
                        if (audit.liveConnections() != 0) throw new IllegalStateException("Write connection leak");
                        FixtureSupport.requireCount(pool, count);
                        JdbcExecutor jdbc = new JdbcExecutor(); jdbc.init(pool);
                        var rows = jdbc.queryEntities(1, count);
                        for (int i = 0; i < count; i++) FixtureSupport.requireRow(rows.get(i), i + 1);
                        jdbc.close();
                        result.put("insert-transaction-rows" + count, events);
                    }
                    write(directory.resolve(orm + ".json"), result);
                    summary.put(orm, "PASS");
                } catch (Throwable failure) {
                    summary.put(orm, Map.of("status", "FAIL", "type", failure.getClass().getName(), "message", String.valueOf(failure.getMessage())));
                    write(directory.resolve("status.json"), summary);
                    throw failure;
                }
                // The next adapter begins with the same common JDBC fixture.
                FixtureSupport.createAndSeed(pool, 1000);
            }
        }
        write(directory.resolve("status.json"), summary);
        write(directory.resolve("PASS.json"), Map.of("adapters", ORMS, "status", "PASS", "note", "Runner must additionally bind this gate to source/candidate/config hashes"));
    }

    private static List<?> query(BenchmarkExecutor executor, String projection, int first, int count) {
        return switch (projection) {
            case "entity" -> executor.queryEntities(first, count);
            case "map" -> executor.queryMaps(first, count);
            case "scalar" -> executor.queryNames(first, count);
            default -> throw new IllegalArgumentException(projection);
        };
    }
    private static List<Map<String, Object>> executions(List<Map<String, Object>> events) {
        return events.stream().filter(e -> e.get("kind").toString().startsWith("execute")).toList();
    }
    private static String normalized(String sql) {
        return sql.toLowerCase(Locale.ROOT).replace("`", "").replaceAll("[a-zA-Z_][a-zA-Z0-9_]*\\.", "")
            .replaceAll("[()\\s]+", " ").trim();
    }
    private static void checkConnections(List<Map<String, Object>> events) {
        for (String kind : List.of("connection.open", "connection.close")) {
            if (events.stream().filter(e -> kind.equals(e.get("kind"))).count() != 1) throw new IllegalStateException("Expected exactly one " + kind);
        }
        if (events.stream().anyMatch(e -> "connection.rollback".equals(e.get("kind")))) throw new IllegalStateException("Unexpected rollback");
    }
    private static Set<String> projection(String sql) {
        String normalized = normalized(sql);
        int end = normalized.indexOf(" from ");
        if (!normalized.startsWith("select ") || end < 0) throw new IllegalStateException("Expected simple SELECT");
        Set<String> columns = new LinkedHashSet<>();
        for (String expression : normalized.substring(7, end).split(",")) {
            String column = expression.trim().split("\\s+")[0];
            if (!columns.add(column)) throw new IllegalStateException("Repeated projection");
        }
        return columns;
    }
    private static void checkQuery(List<Map<String, Object>> events, String type, int first, int count) {
        checkConnections(events);
        var queries = executions(events);
        if (queries.size() != 1) throw new IllegalStateException("Expected exactly one query execution");
        var query = queries.getFirst();
        String sql = normalized(query.get("sql").toString());
        if (!sql.contains(" from tb_user ") || !sql.matches(".* where id >= \\? and id < \\? order by id(?: asc)?$")) {
            throw new IllegalStateException("SQL range/order differs: " + sql);
        }
        if (!projection(sql).equals(type.equals("scalar") ? Set.of("name") : new HashSet<>(FixtureSupport.COLUMNS))) throw new IllegalStateException("SQL column set differs");
        Object bound = query.get("bindings");
        if (!(bound instanceof Map<?, ?> bindings) || bindings.size() != 2) throw new IllegalStateException("Expected two bound parameters");
        checkInteger(bindings.get(1), first); checkInteger(bindings.get(2), first + count);
        if (events.stream().anyMatch(e -> "connection.commit".equals(e.get("kind")))) throw new IllegalStateException("Query unexpectedly commits");
    }
    private static void checkInteger(Object binding, int expected) {
        if (!(binding instanceof Map<?, ?> value) || !Integer.toString(expected).equals(value.get("value")) || !"java.lang.Integer".equals(value.get("javaType"))) {
            throw new IllegalStateException("Integer binding differs");
        }
    }
    private static void checkWrite(List<Map<String, Object>> events, int count) {
        checkConnections(events);
        var writes = executions(events);
        if (writes.size() != count || events.stream().filter(e -> "connection.commit".equals(e.get("kind"))).count() != 1) throw new IllegalStateException("Expected row-wise INSERTs and one commit");
        for (var write : writes) {
            String sql = normalized(write.get("sql").toString());
            if (!sql.startsWith("insert into tb_user ") || !sql.contains(" values ")) throw new IllegalStateException("Unexpected write SQL");
            String columnPart = sql.substring("insert into tb_user ".length(), sql.indexOf(" values "));
            Set<String> columns = new HashSet<>();
            for (String column : columnPart.split(",")) columns.add(column.trim());
            if (!columns.equals(new HashSet<>(FixtureSupport.COLUMNS))) throw new IllegalStateException("INSERT column set differs");
            if (((Map<?, ?>) write.get("bindings")).size() != 17 || !((Map<?, ?>) write.get("bindings")).values().stream().allMatch(v -> v instanceof Map<?, ?>)) throw new IllegalStateException("Missing write bindings");
        }
        if (events.stream().anyMatch(e -> "getGeneratedKeys".equals(e.get("kind")))) throw new IllegalStateException("Generated keys requested for assigned IDs");
    }

    public static Map<String, Object> environment(DruidDataSource pool) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("jdk", System.getProperty("java.runtime.version"));
        result.put("javaVendor", System.getProperty("java.vendor"));
        result.put("os", System.getProperty("os.name") + " " + System.getProperty("os.version"));
        result.put("architecture", System.getProperty("os.arch"));
        result.put("jdbcUrlWithoutCredentials", DataSourceHelper.URL);
        result.put("pool", Map.of("initial", 1, "maximum", 1, "autoCommit", true, "isolation", "READ_COMMITTED", "poolPreparedStatements", false));
        result.put("ddl", FixtureSupport.DDL); result.put("seed", FixtureSupport.SEED);
        try (Connection c = pool.getConnection(); Statement statement = c.createStatement()) {
            result.put("driver", c.getMetaData().getDriverName() + " " + c.getMetaData().getDriverVersion());
            result.put("mysql", c.getMetaData().getDatabaseProductVersion());
            for (String variable : List.of("version", "innodb_buffer_pool_size", "innodb_flush_log_at_trx_commit", "sync_binlog", "log_bin", "transaction_isolation", "character_set_server", "collation_server", "sql_mode", "time_zone")) {
                try (ResultSet rs = statement.executeQuery("SHOW VARIABLES LIKE '" + variable + "'")) {
                    if (rs.next()) result.put(variable, rs.getString(2));
                }
            }
        }
        return result;
    }
    private static void write(Path path, Object value) throws Exception {
        JSON.writerWithDefaultPrettyPrinter().writeValue(path.toFile(), value);
    }
}
