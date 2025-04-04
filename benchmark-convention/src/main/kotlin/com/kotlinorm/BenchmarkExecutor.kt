package com.kotlinorm

import javax.sql.DataSource

interface BenchmarkExecutor {
    /**
     * Initialize the benchmark executor with a data source
     */
    fun init(dataSource: DataSource, listOfMap: List<Map<String, Any>>)

    fun prepareData(listOfMap: List<Map<String, Any>>)

    /**
     * Execute a query, query for single row
     */
    fun querySingleEntity()

    /**
     * Execute an insert, insert a single row
     */
    fun executeInsert()

    /**
     * Clean up resources after the benchmark execution
     */
    fun onDestroy()
}