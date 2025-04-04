package com.kotlinorm.mybatisBenchmark.mapper

import com.baomidou.mybatisplus.core.mapper.BaseMapper
import com.kotlinorm.mybatisBenchmark.dao.User
import org.apache.ibatis.annotations.Mapper

@Mapper
interface UserMapper : BaseMapper<User>