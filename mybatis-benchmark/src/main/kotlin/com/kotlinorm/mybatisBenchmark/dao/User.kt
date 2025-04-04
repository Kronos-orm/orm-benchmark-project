package com.kotlinorm.mybatisBenchmark.dao

import com.baomidou.mybatisplus.annotation.IdType
import com.baomidou.mybatisplus.annotation.TableId
import com.baomidou.mybatisplus.annotation.TableName

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@TableName("tb_user")
class User(
    @TableId(type = IdType.INPUT)
    var id: Long? = null,

    var name: String?,

    var age: Int?
)