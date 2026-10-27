package com.kotlinorm.jpaBenchmark.pojo

import jakarta.persistence.*
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

@Entity
@Table(name = "tb_user")
class User(
    @Id
    @Column(name = "id")
    var id: Int = 0,
    @Column(name = "uid")
    var uid: Long = 0L,
    @Column(name = "name")
    var name: String = "",
    @Column(name = "age")
    var age: Int = 0,
    @Column(name = "sex", columnDefinition = "TINYINT(1)")
    var sex: Boolean = false,
    @Column(name = "height")
    var height: Float = 0f,
    @Column(name = "weight")
    var weight: Float = 0f,
    @Column(name = "score")
    var score: Double = 0.0,
    @Column(name = "salary")
    var salary: BigDecimal = BigDecimal.ZERO,
    @Column(name = "birthday")
    var birthday: LocalDate = LocalDate.of(2000, 1, 1),
    @Column(name = "email")
    var email: String = "",
    @Column(name = "address")
    var address: String = "",
    @Column(name = "comment")
    var comment: ByteArray = byteArrayOf(),
    @Column(name = "version")
    var version: Int = 0,
    @Column(name = "deleted", columnDefinition = "TINYINT(1)")
    var deleted: Boolean = false,
    @Column(name = "create_time")
    var createTime: LocalDateTime = LocalDateTime.of(2020, 1, 1, 0, 0),
    @Column(name = "update_time")
    var updateTime: LocalDateTime = LocalDateTime.of(2020, 1, 1, 0, 0)
)
