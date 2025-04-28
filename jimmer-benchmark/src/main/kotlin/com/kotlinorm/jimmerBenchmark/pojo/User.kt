package com.kotlinorm.jimmerBenchmark.pojo

import org.babyfish.jimmer.sql.Column
import org.babyfish.jimmer.sql.Entity
import org.babyfish.jimmer.sql.GeneratedValue
import org.babyfish.jimmer.sql.GenerationType
import org.babyfish.jimmer.sql.Id
import org.babyfish.jimmer.sql.Serialized
import org.babyfish.jimmer.sql.Table
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/9
 */
@Entity
@Table(name = "tb_user")
interface User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Int
    
    val uid: Long

    val name: String

    val age: Int
    
    val sex: Boolean
    
    val height: Float
    
    val weight: Float
    
    val score: Double

    val salary: BigDecimal
    
    val birthday: LocalDate

    val email: String
    
    val address: String

    @Serialized
//    @Column(sqlType = "BLOB")
    val comment: ByteArray
    
    val version: Int
    
    val deleted: Boolean
    
    val createTime: LocalDateTime
    
    val updateTime: LocalDateTime
}