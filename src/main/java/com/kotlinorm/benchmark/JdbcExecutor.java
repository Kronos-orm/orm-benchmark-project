package com.kotlinorm.benchmark;

import com.kotlinorm.BenchmarkExecutor;
import com.kotlinorm.FixtureRow;
import javax.sql.DataSource;
import java.sql.*;
import java.util.*;

/** Typed full-materialization JDBC baseline with the same pool/connection lifetime. */
public final class JdbcExecutor implements BenchmarkExecutor {
    private DataSource source;
    private List<FixtureRow> inserts = List.of();
    @Override public void init(DataSource source) { this.source = source; }

    private <T> List<T> query(String columns, int firstId, int rowCount, RowReader<T> reader) {
        String sql = "SELECT " + columns + " FROM tb_user WHERE id >= ? AND id < ? ORDER BY id ASC";
        try (Connection c = source.getConnection(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1, firstId); ps.setInt(2, firstId + rowCount);
            try (ResultSet rs = ps.executeQuery()) {
                List<T> result = new ArrayList<>();
                while (rs.next()) result.add(reader.read(rs));
                return result;
            }
        } catch (SQLException failure) { throw new IllegalStateException("JDBC operation failed", failure); }
    }

    @Override public List<Object> queryEntities(int firstId, int rowCount) {
        return query(FixtureSupport.SELECT_COLUMNS, firstId, rowCount, FixtureSupport::readRow);
    }
    @Override public List<Map<String, Object>> queryMaps(int firstId, int rowCount) {
        return query(FixtureSupport.SELECT_COLUMNS, firstId, rowCount, FixtureSupport::readMap);
    }
    @Override public List<String> queryNames(int firstId, int rowCount) {
        return query("name", firstId, rowCount, rs -> rs.getString(1));
    }
    @Override public void prepareInsert(List<FixtureRow> rows) { inserts = List.copyOf(rows); }
    @Override public int insertTransaction() {
        try (Connection connection = source.getConnection()) {
            connection.setAutoCommit(false);
            try {
                int affected = 0;
                // Match ORM row-wise paths: prepare/bind/execute for every row, single commit.
                for (FixtureRow row : inserts) try (PreparedStatement ps = connection.prepareStatement(FixtureSupport.INSERT_SQL)) {
                    FixtureSupport.bind(ps, row); affected += ps.executeUpdate();
                }
                connection.commit();
                return affected;
            } catch (Throwable failure) { connection.rollback(); throw failure; }
        } catch (SQLException failure) { throw new IllegalStateException("JDBC transaction failed", failure); }
    }
    @Override public void close() { inserts = List.of(); }
    private interface RowReader<T> { T read(ResultSet rs) throws SQLException; }
}
