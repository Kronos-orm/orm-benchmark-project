package com.kotlinorm.jpaBenchmark.pojo

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Entity
@Table(name = "tb_user")
data class User(
    @Id
    @Column(name = "id")
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Int? = null,

    @Column(name = "uid")
    val uid: Long? = null,

    @Column(name = "name")
    val name: String? = null,

    @Column(name = "age")
    val age: Int? = null,

    @Column(name = "sex", columnDefinition = "TINYINT(1)")
    var sex: Boolean? = null,

    @Column(name = "height")
    var height: Float? = null,

    @Column(name = "weight")
    var weight: Float? = null,

    @Column(name = "score")
    var score: Double? = null,

    @Column("salary")
    var salary: BigDecimal? = null,

    @Column(name = "birthday")
    var birthday: LocalDate? = null,

    @Column(name = "email")
    var email: String? = null,

    @Column(name = "address")
    var address: String? = null,

    @Column(name = "comment")
    var comment: ByteArray? = null,

    @Column(name = "version")
    var version: Int? = null,

    @Column(name = "deleted", columnDefinition = "TINYINT(1)")
    var deleted: Boolean? = null,

    @Column(name = "create_time")
    var createTime: LocalDateTime? = null,

    @Column(name = "update_time")
    var updateTime: LocalDateTime? = null,
) {
    constructor() : this(
        id = null,
        uid = 0L,
        name = "",
        age = 0,
        sex = true,
        height = 0f,
        weight = 0f,
        score = 0.0,
        salary = BigDecimal.ZERO,
        birthday = null,
        email = "",
        address = "",
        comment = ByteArray(0),
        version = 0,
        deleted = false,
        createTime = null,
        updateTime = null,
    )

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as User

        if (id != other.id) return false
        if (uid != other.uid) return false
        if (age != other.age) return false
        if (sex != other.sex) return false
        if (height != other.height) return false
        if (weight != other.weight) return false
        if (score != other.score) return false
        if (version != other.version) return false
        if (deleted != other.deleted) return false
        if (name != other.name) return false
        if (salary != other.salary) return false
        if (birthday != other.birthday) return false
        if (email != other.email) return false
        if (address != other.address) return false
        if (!comment.contentEquals(other.comment)) return false
        if (createTime != other.createTime) return false
        if (updateTime != other.updateTime) return false

        return true
    }

    override fun hashCode(): Int {
        var result = id ?: 0
        result = 31 * result + (uid?.hashCode() ?: 0)
        result = 31 * result + (age ?: 0)
        result = 31 * result + (sex?.hashCode() ?: 0)
        result = 31 * result + (height?.hashCode() ?: 0)
        result = 31 * result + (weight?.hashCode() ?: 0)
        result = 31 * result + (score?.hashCode() ?: 0)
        result = 31 * result + (version ?: 0)
        result = 31 * result + (deleted?.hashCode() ?: 0)
        result = 31 * result + (name?.hashCode() ?: 0)
        result = 31 * result + (salary?.hashCode() ?: 0)
        result = 31 * result + (birthday?.hashCode() ?: 0)
        result = 31 * result + (email?.hashCode() ?: 0)
        result = 31 * result + (address?.hashCode() ?: 0)
        result = 31 * result + (comment?.contentHashCode() ?: 0)
        result = 31 * result + (createTime?.hashCode() ?: 0)
        result = 31 * result + (updateTime?.hashCode() ?: 0)
        return result
    }
}