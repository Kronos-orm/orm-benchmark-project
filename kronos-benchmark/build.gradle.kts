
group = "com.kotlinorm"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

repositories {
    mavenCentral()
    maven {
        name = "Central Portal Snapshots"
        url = uri("https://central.sonatype.com/repository/maven-snapshots/")
    }
}

plugins {
    kotlin("jvm") version "2.1.0"
    kotlin("plugin.spring") version "1.9.25"
    id("io.ktor.plugin") version "3.0.1"
    id("org.springframework.boot") version "3.4.4"
    id("io.spring.dependency-management") version "1.1.7"
    id("com.kotlinorm.kronos-gradle-plugin") version "0.0.1"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    implementation("com.kotlinorm:kronos-core:0.0.2-SNAPSHOT")
    implementation("com.kotlinorm:kronos-jdbc-wrapper:0.0.2-SNAPSHOT")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xjsr305=strict")
    }
}

tasks.withType<Test> {
    useJUnitPlatform()
}
