package com.kotlinorm.mybatisBenchmark.mapper

import com.baomidou.mybatisplus.core.mapper.BaseMapper
import com.kotlinorm.mybatisBenchmark.dao.User
import org.apache.ibatis.annotations.Mapper

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Mapper
interface UserMapper: BaseMapper<User>