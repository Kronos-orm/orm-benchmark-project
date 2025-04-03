dependencyResolutionManagement {
    versionCatalogs {
        create("libs") {
            from(files("./libs.versions.toml"))
        }
    }
    @Suppress("UnstableApiUsage")
    repositoriesMode.set(RepositoriesMode.PREFER_PROJECT)
    @Suppress("UnstableApiUsage")
    repositories {
        mavenCentral()
        gradlePluginPortal()
        maven {
            name = "Central Portal Snapshots"
            url = uri("https://central.sonatype.com/repository/maven-snapshots/")
        }
        maven("https://dl.bintray.com/kotlin/kotlin-eap")
        maven("https://maven.aliyun.com/repository/public")
        maven("https://maven.aliyun.com/nexus/content/groups/public/")
    }
}

pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
        maven("https://dl.bintray.com/kotlin/kotlin-eap")
        maven("https://maven.aliyun.com/repository/public")
        maven("https://maven.aliyun.com/nexus/content/groups/public/")
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.9.0"
}

rootProject.name = "orm-benchmark-project"

include(":jpa-benchmark")
include(":kronos-benchmark")
include(":mybatis-benchmark")
