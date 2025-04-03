package com.kotlinorm.jpaBenchmark.controller

import com.kotlinorm.jpaBenchmark.pojo.User
import com.kotlinorm.jpaBenchmark.repo.UserRepository
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */

@Service
class UserService(
    @Autowired val userRepository: UserRepository
) {

    fun createUser(users: List<User>) {
        userRepository.saveAll<User>(users)
    }

    fun getAllUsers(): List<User?> {
        return userRepository.findAll()
    }

}