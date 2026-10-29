package com.kotlinorm.benchmark;

import com.kotlinorm.FixtureRow;
import javax.sql.DataSource;
import java.math.BigDecimal;
import java.sql.*;
import java.time.*;
import java.util.*;

/** Common JDBC schema/seed only; no participating ORM owns another ORM's fixture. */
public final class FixtureSupport {
    public static final long SEED = 2026102704L;
    public static final List<String> COLUMNS = List.of("id", "uid", "name", "age", "sex", "height", "weight", "score", "salary", "birthday", "email", "address", "comment", "version", "deleted", "create_time", "update_time");
    public static final List<String> PROPERTIES = List.of("id", "uid", "name", "age", "sex", "height", "weight", "score", "salary", "birthday", "email", "address", "comment", "version", "deleted", "createTime", "updateTime");
    public static final String SELECT_COLUMNS = String.join(", ", COLUMNS.stream().map(c -> "`" + c + "`").toList());
    public static final String INSERT_SQL = "INSERT INTO tb_user (" + SELECT_COLUMNS + ") VALUES (" + String.join(",", Collections.nCopies(17, "?")) + ")";
    public static final String DDL = """
        CREATE TABLE tb_user (
          id INT NOT NULL PRIMARY KEY, uid BIGINT NOT NULL, name VARCHAR(64) NOT NULL,
          age INT NOT NULL, sex TINYINT(1) NOT NULL, height FLOAT NOT NULL, weight FLOAT NOT NULL,
          score DOUBLE NOT NULL, salary DECIMAL(18,2) NOT NULL, birthday DATE NOT NULL,
          email VARCHAR(128) NOT NULL, address VARCHAR(160) NOT NULL, comment VARBINARY(128) NOT NULL,
          version INT NOT NULL, deleted TINYINT(1) NOT NULL,
          create_time DATETIME(3) NOT NULL, update_time DATETIME(3) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
        """;
    private FixtureSupport() {}

    public static FixtureRow row(int id) {
        byte[] bytes = new byte[100];
        new Random(SEED ^ id).nextBytes(bytes);
        LocalDateTime created = LocalDateTime.of(2020, 1, 1, 0, 0).plusSeconds(id);
        return new FixtureRow(id, 10000000000L + id, String.format(Locale.ROOT, "user-%014d", id),
            18 + id % 70, id % 2 == 0, 1.5f + (id % 50) / 100f, 40f + (id % 500) / 10f,
            (id % 10000) / 100.0, BigDecimal.valueOf(1000000L + id, 2),
            LocalDate.of(1970, 1, 1).plusDays(id % 18000), "user" + id + "@example.test",
            "Synthetic address " + id, bytes, id % 5, false, created, created.plusHours(1));
    }

    public static List<FixtureRow> rows(int count) {
        ArrayList<FixtureRow> rows = new ArrayList<>(count);
        for (int id = 1; id <= count; id++) rows.add(row(id));
        return rows;
    }

    public static void createAndSeed(DataSource source, int count) throws Exception {
        try (Connection connection = source.getConnection(); Statement statement = connection.createStatement()) {
            statement.execute("DROP TABLE IF EXISTS tb_user");
            statement.execute(DDL);
        }
        if (count > 0) try (Connection connection = source.getConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement insert = connection.prepareStatement(INSERT_SQL)) {
                for (int id = 1; id <= count; id++) {
                    bind(insert, row(id)); insert.addBatch();
                    if (id % 1000 == 0) insert.executeBatch();
                }
                if (count % 1000 != 0) insert.executeBatch();
                connection.commit();
            } catch (Throwable failure) { connection.rollback(); throw failure; }
        }
        requireCount(source, count);
    }

    /** Iteration-level reset for one SingleShotTime invocation, never on the measured call path. */
    public static void resetWrites(DataSource source) throws Exception {
        try (Connection connection = source.getConnection(); Statement statement = connection.createStatement()) {
            statement.execute("TRUNCATE TABLE tb_user");
        }
    }

    public static void requireCount(DataSource source, int expected) throws Exception {
        try (Connection c = source.getConnection(); Statement s = c.createStatement(); ResultSet rs = s.executeQuery("SELECT COUNT(*) FROM tb_user")) {
            rs.next(); if (rs.getInt(1) != expected) throw new IllegalStateException("Unexpected fixture row count");
        }
    }

    public static FixtureRow readRow(ResultSet rs) throws SQLException {
        return new FixtureRow(rs.getInt(1), rs.getLong(2), rs.getString(3), rs.getInt(4), rs.getBoolean(5), rs.getFloat(6), rs.getFloat(7), rs.getDouble(8), rs.getBigDecimal(9), rs.getObject(10, LocalDate.class), rs.getString(11), rs.getString(12), rs.getBytes(13), rs.getInt(14), rs.getBoolean(15), rs.getObject(16, LocalDateTime.class), rs.getObject(17, LocalDateTime.class));
    }

    public static Map<String, Object> readMap(ResultSet rs) throws SQLException {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", rs.getInt(1));
        result.put("uid", rs.getLong(2));
        result.put("name", rs.getString(3));
        result.put("age", rs.getInt(4));
        result.put("sex", rs.getBoolean(5));
        result.put("height", rs.getFloat(6));
        result.put("weight", rs.getFloat(7));
        result.put("score", rs.getDouble(8));
        result.put("salary", rs.getBigDecimal(9));
        result.put("birthday", rs.getObject(10, LocalDate.class));
        result.put("email", rs.getString(11));
        result.put("address", rs.getString(12));
        result.put("comment", rs.getBytes(13));
        result.put("version", rs.getInt(14));
        result.put("deleted", rs.getBoolean(15));
        result.put("create_time", rs.getObject(16, LocalDateTime.class));
        result.put("update_time", rs.getObject(17, LocalDateTime.class));
        return result;
    }

    public static void bind(PreparedStatement ps, FixtureRow row) throws SQLException {
        ps.setInt(1, row.getId());
        ps.setLong(2, row.getUid());
        ps.setString(3, row.getName());
        ps.setInt(4, row.getAge());
        ps.setBoolean(5, row.getSex());
        ps.setFloat(6, row.getHeight());
        ps.setFloat(7, row.getWeight());
        ps.setDouble(8, row.getScore());
        ps.setBigDecimal(9, row.getSalary());
        ps.setObject(10, row.getBirthday());
        ps.setString(11, row.getEmail());
        ps.setString(12, row.getAddress());
        ps.setBytes(13, row.getComment());
        ps.setInt(14, row.getVersion());
        ps.setBoolean(15, row.getDeleted());
        ps.setObject(16, row.getCreateTime());
        ps.setObject(17, row.getUpdateTime());
    }

    /** Reflection only for correctness checks, never inside a benchmark method. */
    public static Map<String, Object> normalize(Object value) throws Exception {
        Map<String, Object> result = new LinkedHashMap<>();
        if (value instanceof Map<?, ?> map) {
            for (var entry : map.entrySet()) {
                String key = entry.getKey().toString();
                int index = COLUMNS.indexOf(key);
                if (index < 0) index = PROPERTIES.indexOf(key);
                if (index < 0) throw new IllegalStateException("Unexpected map key: " + key);
                result.put(PROPERTIES.get(index), entry.getValue());
            }
        } else {
            for (String property : PROPERTIES) {
                var getter = value.getClass().getMethod("get" + Character.toUpperCase(property.charAt(0)) + property.substring(1));
                getter.trySetAccessible();
                result.put(property, getter.invoke(value));
            }
        }
        if (!result.keySet().equals(new HashSet<>(PROPERTIES))) throw new IllegalStateException("Projection key mismatch");
        return result;
    }

    public static void requireRow(Object actual, int id) throws Exception {
        Map<String, Object> expected = normalize(row(id)), values = normalize(actual);
        for (String property : PROPERTIES) {
            Object a = values.get(property), e = expected.get(property);
            // Native map APIs expose JDBC temporals in some frameworks. Compare their logical
            // values outside timing and retain their actual runtime types in the SQL audit report.
            if (e instanceof LocalDate && a instanceof java.sql.Date date) a = date.toLocalDate();
            if (e instanceof LocalDateTime && a instanceof Timestamp timestamp) a = timestamp.toLocalDateTime();
            boolean equal = e instanceof byte[] bytes ? a instanceof byte[] other && Arrays.equals(bytes, other)
                : e instanceof BigDecimal number ? a instanceof BigDecimal other && number.equals(other)
                : Objects.equals(e, a);
            if (!equal) throw new IllegalStateException("Field mismatch at id=" + id + " property=" + property + " actualType=" + (a == null ? "null" : a.getClass().getName()));
        }
    }
}
