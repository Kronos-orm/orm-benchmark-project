package com.kotlinorm

import javax.sql.DataSource

interface BenchmarkExecutor {
    /**
     * Initialize the benchmark executor with a data source
     */
    fun init(dataSource: DataSource)

    /**
     * Execute a query, query for single row
     */
    fun querySingleEntity()

    /**
     * Execute an insert, insert a single row
     */
    fun executeInsert1000()

    /**
     * Clean up resources after the benchmark execution
     */
    fun onDestroy()
}