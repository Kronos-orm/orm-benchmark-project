package com.kotlinorm.benchmark;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;

/** Read-only environment verification immediately before pilot/measurement/profile stages. */
public final class InspectEnvironment {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected output file path");
        if (args[0].equals("--pool-config-only")) {
            try (var pool = DataSourceHelper.uninitializedPool()) {
                if (pool.getTimeBetweenEvictionRunsMillis() != DataSourceHelper.HOUSEKEEPING_INTERVAL_MILLIS || pool.getMaxActive() != 1 || pool.isTestWhileIdle()) {
                    throw new IllegalStateException("Unexpected shared pool policy");
                }
                System.out.println("PASS: shared Druid settings validated without secrets, init or database access");
            }
            return;
        }
        try (var pool = DataSourceHelper.openPool()) {
            new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(Path.of(args[0]).toFile(), ValidateBenchmark.environment(pool));
        }
    }
}
