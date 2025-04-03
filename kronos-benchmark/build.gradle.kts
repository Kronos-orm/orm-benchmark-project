plugins {
    alias { libs.plugins.kotlin.jvm }
    alias { libs.plugins.kronos.gradle.plugin }
}

dependencies {
    implementation(libs.kronos.core)
    implementation(libs.kronos.jdbc.wrapper)
}
