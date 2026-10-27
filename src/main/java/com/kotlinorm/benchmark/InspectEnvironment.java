package com.kotlinorm.benchmark;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;

/** Read-only environment verification immediately before pilot/measurement/profile stages. */
public final class InspectEnvironment {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected output file path");
        try (var pool = DataSourceHelper.openPool()) {
            new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(Path.of(args[0]).toFile(), ValidateBenchmark.environment(pool));
        }
    }
}
