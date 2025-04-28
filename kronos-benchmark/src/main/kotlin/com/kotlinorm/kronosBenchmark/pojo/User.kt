package com.kotlinorm.kronosBenchmark.pojo

import com.kotlinorm.annotations.PrimaryKey
import com.kotlinorm.annotations.Table
import com.kotlinorm.interfaces.KPojo
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

@Table("tb_user")
data class User(
    @PrimaryKey(identity = true)
    var id: Int? = null,
    var uid: Long? = null,
    var name: String? = null,
    var age: Int? = null,
    var sex: Boolean? = null,
    var height: Float? = null,
    var weight: Float? = null,
    var score: Double? = null,
    var salary: BigDecimal? = null,
    var birthday: LocalDate? = null,
    var email: String? = null,
    var address: String? = null,
    var comment: ByteArray? = null,
    var version: Int? = null,
    var deleted: Boolean? = null,
    var createTime: LocalDateTime? = null,
    var updateTime: LocalDateTime? = null,
): KPojo {
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
        if (salary != other.salary) return false
        if (version != other.version) return false
        if (deleted != other.deleted) return false
        if (name != other.name) return false
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
        result = 31 * result + (salary?.hashCode() ?: 0)
        result = 31 * result + (version ?: 0)
        result = 31 * result + (deleted?.hashCode() ?: 0)
        result = 31 * result + (name?.hashCode() ?: 0)
        result = 31 * result + (birthday?.hashCode() ?: 0)
        result = 31 * result + (email?.hashCode() ?: 0)
        result = 31 * result + (address?.hashCode() ?: 0)
        result = 31 * result + (comment?.contentHashCode() ?: 0)
        result = 31 * result + (createTime?.hashCode() ?: 0)
        result = 31 * result + (updateTime?.hashCode() ?: 0)
        return result
    }
}
