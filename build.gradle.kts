plugins {
    java
    application
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.jpa) apply false
    alias(libs.plugins.kotlin.noArg) apply false
    alias(libs.plugins.ksp) apply false
}

java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }
application { mainClass.set("org.openjdk.jmh.Main") }

dependencies {
    implementation(project(":benchmark-convention"))
    implementation(project(":kronos-benchmark"))
    implementation(project(":jpa-benchmark"))
    implementation(project(":jimmer-benchmark"))
    implementation(project(":ktorm-benchmark"))
    implementation(project(":mybatis-benchmark"))
    implementation(libs.driver.jdbc.mysql)
    implementation(libs.druid)
    implementation(libs.jmh.core)
    annotationProcessor(libs.jmh.generator)
    implementation(libs.jackson.module)
    implementation("org.jetbrains.kotlin:kotlin-reflect:2.4.21")
}

allprojects {
    dependencyLocking { lockAllConfigurations() }
    // Gradle dependency locking is incompatible with failOnDynamicVersions/failOnChangingVersions.
    // Lockfiles and the exported runtime hashes bind the resolved graph for every CI shard.
}
subprojects {
    plugins.withId("org.jetbrains.kotlin.jvm") {
        extensions.configure<org.jetbrains.kotlin.gradle.dsl.KotlinJvmProjectExtension> {
            jvmToolchain(21)
        }
        dependencies.add("implementation", dependencies.platform("org.jetbrains.kotlin:kotlin-bom:2.4.21"))
    }
}

tasks.register<JavaExec>("validateBenchmark") {
    group = "verification"
    dependsOn(tasks.classes)
    mainClass.set("com.kotlinorm.benchmark.ValidateBenchmark")
    classpath = sourceSets.main.get().runtimeClasspath
    args(providers.gradleProperty("validationDir").orElse("build/validation").get())
}

tasks.register("writeRuntimeClasspath") {
    dependsOn(tasks.classes)
    val target = layout.buildDirectory.file("runtime-classpath.txt")
    outputs.file(target)
    doLast { target.get().asFile.writeText(sourceSets.main.get().runtimeClasspath.filter { it.exists() }.asPath) }
}
