pluginManagement {
    val candidate = providers.gradleProperty("kronosCandidateRepo")
        .orElse(providers.environmentVariable("KRONOS_CANDIDATE_REPO"))
        .orNull ?: error("Set kronosCandidateRepo/KRONOS_CANDIDATE_REPO to the approved isolated candidate repository")
    repositories {
        exclusiveContent {
            forRepository { maven { name = "ApprovedKronosCandidatePlugins"; url = uri(candidate) } }
            filter { includeGroupByRegex("com\\.kotlinorm(\\..*)?") }
        }
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    versionCatalogs { create("libs") { from(files("libs.versions.toml")) } }
    val candidate = providers.gradleProperty("kronosCandidateRepo")
        .orElse(providers.environmentVariable("KRONOS_CANDIDATE_REPO"))
        .orNull ?: error("Approved Kronos candidate repository is required")
    repositories {
        exclusiveContent {
            forRepository { maven { name = "ApprovedKronosCandidate"; url = uri(candidate) } }
            filter { includeGroupByRegex("com\\.kotlinorm(\\..*)?") }
        }
        mavenCentral()
    }
}
rootProject.name = "orm-benchmark-project"
include(":benchmark-convention", ":kronos-benchmark", ":jpa-benchmark", ":jimmer-benchmark", ":ktorm-benchmark", ":mybatis-benchmark")
