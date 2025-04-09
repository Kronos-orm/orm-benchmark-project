package com.kotlinorm.jimmerBenchmark.pojo

import org.babyfish.jimmer.sql.Entity
import org.babyfish.jimmer.sql.GeneratedValue
import org.babyfish.jimmer.sql.GenerationType
import org.babyfish.jimmer.sql.Id
import org.babyfish.jimmer.sql.Table

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

    val name: String

    val age: Int

}