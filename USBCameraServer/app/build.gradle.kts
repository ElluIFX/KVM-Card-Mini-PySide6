plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.webusbkvm.camera"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.webusbkvm.camera"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // NanoHTTPd — lightweight HTTP server for MJPEG streaming
    implementation("org.nanohttpd:nanohttpd:2.3.1")
}
