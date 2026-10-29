plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.ksp)
}
dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.jimmer.core)
    implementation(libs.jimmer.sql)
    // Jimmer-generated drafts reference these annotations; they are not a transitive compile dependency.
    implementation(libs.jackson.annotations)
    ksp(libs.jimmer.ksp)
    // Resolve one current KSP API on the processor classpath; the processor targets an older compatible API.
    ksp(libs.ksp.api)
}
