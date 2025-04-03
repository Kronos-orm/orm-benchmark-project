package com.kotlinorm.jpaBenchmark.repo

import com.kotlinorm.jpaBenchmark.pojo.User
import org.springframework.data.jpa.repository.JpaRepository

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
interface UserRepository: JpaRepository<User, Int> {
}