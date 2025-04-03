plugins {
	alias { libs.plugins.kotlin.jvm }
}

dependencies {
	implementation(project(":jpa-benchmark"))
	implementation(project(":kronos-benchmark"))
	implementation(project(":mybatis-benchmark"))
	implementation(libs.driver.jdbc.mysql)
	implementation(libs.druid)
	testImplementation(libs.kotlin.test)
	testImplementation(libs.kotlin.reflect)
}