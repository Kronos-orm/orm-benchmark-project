plugins {
	alias { libs.plugins.kotlin.jvm }
	alias { libs.plugins.kotlinx.benchmark}
	alias { libs.plugins.kotlin.allopen }
}

allOpen {
	annotation("org.openjdk.jmh.annotations.State")
}

benchmark {
	targets {
		register("main")
	}

	configurations {
		named("main") {
			warmups = 5
			iterations = 10
			iterationTime = 3
			iterationTimeUnit = "s"
			reportFormat = "csv"
		}
	}
}


dependencies {
	implementation(project(":benchmark-convention"))
	implementation(project(":jpa-benchmark"))
	implementation(project(":kronos-benchmark"))
	implementation(project(":mybatis-benchmark"))
	implementation(libs.benchmark.runtime)
	implementation(libs.driver.jdbc.mysql)
	implementation(libs.druid)
	testImplementation(libs.kotlin.test)
	testImplementation(libs.kotlin.reflect)
}