package com.kotlinorm.benchmark;

import javax.sql.DataSource;
import java.io.PrintWriter;
import java.lang.reflect.*;
import java.sql.*;
import java.util.*;
import java.util.logging.Logger;

/** Audit-only JDBC proxy. This class is never installed on a timed JMH path. */
public final class SqlAudit implements DataSource {
    private final DataSource delegate;
    private final List<Map<String, Object>> events = new ArrayList<>();
    private int liveConnections;
    public SqlAudit(DataSource delegate) { this.delegate = delegate; }
    public synchronized void reset() {
        if (liveConnections != 0) throw new IllegalStateException("Leaked connection before audit reset");
        events.clear();
    }
    public synchronized List<Map<String, Object>> snapshot() { return List.copyOf(events); }
    public synchronized int liveConnections() { return liveConnections; }
    private synchronized void event(String kind, Object... entries) {
        Map<String, Object> value = new LinkedHashMap<>(); value.put("kind", kind);
        for (int i = 0; i < entries.length; i += 2) value.put(entries[i].toString(), entries[i + 1]);
        events.add(value);
    }
    private static Object invoke(Object target, Method method, Object[] args) throws Throwable {
        try { return method.invoke(target, args); }
        catch (InvocationTargetException failure) { throw failure.getCause(); }
    }
    @Override public Connection getConnection() throws SQLException { return wrap(delegate.getConnection()); }
    @Override public Connection getConnection(String username, String password) throws SQLException {
        throw new SQLFeatureNotSupportedException("Audit uses the dedicated pool credentials only");
    }
    private Connection wrap(Connection connection) {
        synchronized (this) { liveConnections++; }
        event("connection.open");
        boolean[] closed = {false};
        return (Connection) Proxy.newProxyInstance(SqlAudit.class.getClassLoader(), new Class<?>[]{Connection.class}, (proxy, method, args) -> {
            String name = method.getName();
            if (name.equals("unwrap") && ((Class<?>) args[0]).isInstance(proxy)) return proxy;
            if (name.equals("isWrapperFor") && ((Class<?>) args[0]).isInstance(proxy)) return true;
            if (name.equals("close")) {
                if (!closed[0]) {
                    try { return invoke(connection, method, args); }
                    finally { closed[0] = true; synchronized (this) { liveConnections--; } event("connection.close"); }
                }
                return null;
            }
            if (name.equals("prepareStatement")) {
                Object result = invoke(connection, method, args);
                event("prepare", "sql", args[0], "options", options(args));
                return statement((Statement) result, args[0].toString(), (Connection) proxy);
            }
            if (name.equals("createStatement")) return statement((Statement) invoke(connection, method, args), null, (Connection) proxy);
            if (Set.of("commit", "rollback", "setAutoCommit", "setTransactionIsolation", "unwrap").contains(name)) {
                event("connection." + name, "arguments", options(args));
            }
            return invoke(connection, method, args);
        });
    }
    private static List<String> options(Object[] args) {
        if (args == null) return List.of();
        List<String> result = new ArrayList<>();
        for (Object arg : args) {
            if (arg instanceof int[] array) result.add(Arrays.toString(array));
            else if (arg instanceof String[] array) result.add(Arrays.toString(array));
            else result.add(String.valueOf(arg));
        }
        return result;
    }
    private Object statement(Statement statement, String sql, Connection connection) {
        Map<Integer, Map<String, Object>> bindings = new TreeMap<>();
        Class<?> type = statement instanceof PreparedStatement ? PreparedStatement.class : Statement.class;
        return Proxy.newProxyInstance(SqlAudit.class.getClassLoader(), new Class<?>[]{type}, (proxy, method, args) -> {
            String name = method.getName();
            if (name.equals("getConnection")) return connection;
            if (name.equals("unwrap") && ((Class<?>) args[0]).isInstance(proxy)) return proxy;
            if (name.equals("isWrapperFor") && ((Class<?>) args[0]).isInstance(proxy)) return true;
            if (name.equals("clearParameters")) bindings.clear();
            if (name.startsWith("set") && args != null && args.length >= 2 && args[0] instanceof Integer index) {
                Object value = args[1];
                Map<String, Object> bound = new LinkedHashMap<>();
                bound.put("method", name);
                bound.put("javaType", value == null ? "null" : value.getClass().getName());
                bound.put("value", value instanceof byte[] bytes ? HexFormat.of().formatHex(bytes) : String.valueOf(value));
                if (args.length > 2) bound.put("typeOptions", options(Arrays.copyOfRange(args, 2, args.length)));
                bindings.put(index, bound);
            }
            if (name.startsWith("execute") || name.equals("addBatch") || name.equals("getGeneratedKeys")) {
                String actualSql = sql == null && args != null && args.length > 0 && args[0] instanceof String ? args[0].toString() : sql;
                event(name, "sql", actualSql, "bindings", new TreeMap<>(bindings));
            }
            return invoke(statement, method, args);
        });
    }
    @Override public PrintWriter getLogWriter() throws SQLException { return delegate.getLogWriter(); }
    @Override public void setLogWriter(PrintWriter value) throws SQLException { delegate.setLogWriter(value); }
    @Override public void setLoginTimeout(int value) throws SQLException { delegate.setLoginTimeout(value); }
    @Override public int getLoginTimeout() throws SQLException { return delegate.getLoginTimeout(); }
    @Override public Logger getParentLogger() throws SQLFeatureNotSupportedException { return delegate.getParentLogger(); }
    @Override public <T> T unwrap(Class<T> type) throws SQLException {
        if (type.isInstance(this)) return type.cast(this);
        throw new SQLException("Cannot unwrap the audit DataSource");
    }
    @Override public boolean isWrapperFor(Class<?> type) { return type.isInstance(this); }
}
