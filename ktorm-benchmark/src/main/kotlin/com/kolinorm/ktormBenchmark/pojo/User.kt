package com.kolinorm.ktormBenchmark.pojo

import org.ktorm.entity.Entity
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

/**
 *@program: orm-benchmark-project
 *@author: Jieyao Lu
 *@description:
 *@create: 2025/4/7 10:38
 **/
interface User : Entity<User> {
    companion object : Entity.Factory<User>()
    val id: Int
    var uid: Long
    var name: String
    var age: Int
    var sex: Boolean
    var height: Float
    var weight: Float
    var score: Double
    var salary: BigDecimal
    var birthday: LocalDate
    var email: String
    var address: String
    var comment: ByteArray
    var version: Int
    var deleted: Boolean
    var createTime: LocalDateTime
    var updateTime: LocalDateTime
}