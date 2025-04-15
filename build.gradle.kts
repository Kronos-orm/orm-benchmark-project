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
	implementation(project(":jimmer-benchmark"))
	implementation(project(":jpa-benchmark"))
	implementation(project(":kronos-benchmark"))
	implementation(project(":ktorm-benchmark"))
	implementation(project(":mybatis-benchmark"))
	implementation(libs.benchmark.runtime)
	implementation(libs.driver.jdbc.mysql)
	implementation(libs.druid)
	implementation(libs.datafaker)
	implementation(libs.dataframe)
	implementation(libs.bundles.kandy)
}

tasks.register<JavaExec>("generateBenchmarkReport") {
	mainClass.set("com.kotlinorm.benchmark.utils.BenchmarkReporterKt")
	classpath = sourceSets.main.get().runtimeClasspath

	doFirst {
		val csvDir = layout.buildDirectory.dir("reports/benchmarks")
		val csvFile = csvDir.get().asFileTree
			.matching { include("**/main.csv") }
			.singleFile

		args = listOf(
			csvFile.absolutePath,
			layout.buildDirectory.dir("reports/benchmark-report").get().asFile.absolutePath
		)
	}
}