package com.kolinorm.ktormBenchmark.table

import com.kolinorm.ktormBenchmark.pojo.User
import org.ktorm.schema.Table
import org.ktorm.schema.blob
import org.ktorm.schema.boolean
import org.ktorm.schema.bytes
import org.ktorm.schema.date
import org.ktorm.schema.datetime
import org.ktorm.schema.decimal
import org.ktorm.schema.double
import org.ktorm.schema.float
import org.ktorm.schema.int
import org.ktorm.schema.long
import org.ktorm.schema.varchar

object Users: Table<User>("tb_user") {
    val id = int("id").primaryKey().bindTo { it.id }
    val uid = long("uid").bindTo { it.uid }
    val name = varchar("name").bindTo { it.name }
    val age = int("age").bindTo { it.age }
    val sex = boolean("sex").bindTo { it.sex }
    val height = float("height").bindTo { it.height }
    val weight = float("weight").bindTo { it.weight }
    val score = double("score").bindTo { it.score }
    val salary = decimal("salary").bindTo { it.salary }
    val birthday = date("birthday").bindTo { it.birthday }
    val email = varchar("email").bindTo { it.email }
    val address = varchar("address").bindTo { it.address }
    val comment = blob("comment").bindTo { it.comment }
    val version = int("version").bindTo { it.version }
    val deleted = boolean("deleted").bindTo { it.deleted }
    val createTime = datetime("create_time").bindTo { it.createTime }
    val updateTime = datetime("update_time").bindTo { it.updateTime }
}