package com.kotlinorm.mybatisBenchmark.service.impl

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl
import com.kotlinorm.mybatisBenchmark.dao.User
import com.kotlinorm.mybatisBenchmark.mapper.UserMapper
import com.kotlinorm.mybatisBenchmark.service.UserService
import org.springframework.stereotype.Service

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Service
class UserServiceImpl : ServiceImpl<UserMapper, User>(), UserService {

}