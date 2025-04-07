package com.kolinorm.ktormBenchmark.table

import com.kolinorm.ktormBenchmark.pojo.User
import org.ktorm.schema.Table
import org.ktorm.schema.int
import org.ktorm.schema.varchar

object Users: Table<User>("tb_user") {
    val id = int("id").primaryKey().bindTo { it.id }
    val name = varchar("name").bindTo { it.name }
    val age = int("age").bindTo { it.age }
}