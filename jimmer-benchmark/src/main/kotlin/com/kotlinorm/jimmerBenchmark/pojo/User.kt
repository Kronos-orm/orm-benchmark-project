package com.kotlinorm.jimmerBenchmark.pojo

import org.babyfish.jimmer.sql.*
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

@Entity
@Table(name = "tb_user")
interface User {
    @Id
    @Column(name = "id")
    val id: Int
    @Column(name = "uid")
    val uid: Long
    @Column(name = "name")
    val name: String
    @Column(name = "age")
    val age: Int
    @Column(name = "sex")
    val sex: Boolean
    @Column(name = "height")
    val height: Float
    @Column(name = "weight")
    val weight: Float
    @Column(name = "score")
    val score: Double
    @Column(name = "salary")
    val salary: BigDecimal
    @Column(name = "birthday")
    val birthday: LocalDate
    @Column(name = "email")
    val email: String
    @Column(name = "address")
    val address: String
    @Column(name = "comment")
    val comment: ByteArray
    @Column(name = "version")
    val version: Int
    @Column(name = "deleted")
    val deleted: Boolean
    @Column(name = "create_time")
    val createTime: LocalDateTime
    @Column(name = "update_time")
    val updateTime: LocalDateTime
}
