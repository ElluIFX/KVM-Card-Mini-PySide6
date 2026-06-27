@echo off
setlocal enabledelayedexpansion

REM === Configuration ===
set JAVA_HOME=D:\devel\jdk17
set ANDROID_SDK=D:\devel\android-sdk
set APP_NAME=USBCameraServer

set BUILD_TOOLS=%ANDROID_SDK%\build-tools\34.0.0
set PLATFORM=%ANDROID_SDK%\platforms\android-34
set AAPT2=%BUILD_TOOLS%\aapt2.exe
set D8=%BUILD_TOOLS%\d8.bat
set APKSIGNER=%BUILD_TOOLS%\apksigner.bat
set JAVAC=%JAVA_HOME%\bin\javac.exe
set JAR=%JAVA_HOME%\bin\jar.exe

set PROJECT_DIR=%~dp0
set SRC_DIR=%PROJECT_DIR%app\src\main\java
set RES_DIR=%PROJECT_DIR%app\src\main\res
set BUILD_DIR=%PROJECT_DIR%build
set GEN_DIR=%BUILD_DIR%\gen
set CLASSES_DIR=%BUILD_DIR%\classes
set DEX_DIR=%BUILD_DIR%\dex
set LIB_DIR=%PROJECT_DIR%libs

echo === USB Camera Server Build ===
echo JAVA_HOME=%JAVA_HOME%
echo ANDROID_SDK=%ANDROID_SDK%

REM === Clean ===
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%" "%GEN_DIR%" "%CLASSES_DIR%" "%DEX_DIR%"
mkdir "%LIB_DIR%" 2>nul

REM === Libraries (NanoHTTPd) ===
set CLASSPATH=%PLATFORM%\android.jar
if not exist "%LIB_DIR%\nanohttpd-2.3.1.jar" (
    echo Downloading NanoHTTPd...
    curl -L -o "%LIB_DIR%\nanohttpd-2.3.1.jar" "https://repo1.maven.org/maven2/org/nanohttpd/nanohttpd/2.3.1/nanohttpd-2.3.1.jar"
)
if exist "%LIB_DIR%\nanohttpd-2.3.1.jar" (
    set CLASSPATH=!CLASSPATH!;%LIB_DIR%\nanohttpd-2.3.1.jar
    echo NanoHTTPd found
)

REM === Step 1: Compile resources with aapt2 ===
echo.
echo --- Step 1: Compile resources ---
"%AAPT2%" compile -o "%BUILD_DIR%\res.zip" --dir "%RES_DIR%"
if errorlevel 1 goto :error

REM Link resources into a temporary APK
"%AAPT2%" link -o "%BUILD_DIR%\base.apk" ^
    -I "%PLATFORM%\android.jar" ^
    --manifest "%PROJECT_DIR%app\src\main\AndroidManifest.xml" ^
    --java "%GEN_DIR%" ^
    "%BUILD_DIR%\res.zip" ^
    --auto-add-overlay
if errorlevel 1 goto :error

echo Resources compiled OK

REM === Step 2: Compile Java sources ===
echo.
echo --- Step 2: Compile Java ---
dir /s /b "%SRC_DIR%\*.java" > "%BUILD_DIR%\sources.txt"
rem Add R.java from aapt2
"%JAVAC%" -d "%CLASSES_DIR%" ^
    -cp "%CLASSPATH%" ^
    -source 1.8 -target 1.8 ^
    -bootclasspath "%PLATFORM%\android.jar" ^
    @"%BUILD_DIR%\sources.txt" ^
    "%GEN_DIR%\com\webusbkvm\camera\R.java" 2>nul
if errorlevel 1 (
    rem Retry without gen R.java
    "%JAVAC%" -d "%CLASSES_DIR%" -cp "%CLASSPATH%" -source 1.8 -target 1.8 @"%BUILD_DIR%\sources.txt"
    if errorlevel 1 goto :error
)

echo Java compiled OK

REM === Step 3: Extract NanoHTTPd classes ===
echo.
echo --- Step 3: Extract NanoHTTPd ---
if exist "%LIB_DIR%\nanohttpd-2.3.1.jar" (
    cd "%CLASSES_DIR%"
    "%JAR%" xf "%LIB_DIR%\nanohttpd-2.3.1.jar"
    cd "%PROJECT_DIR%"
)

REM === Step 4: Convert to DEX ===
echo.
echo --- Step 4: DEX ---
"%D8%" --lib "%PLATFORM%\android.jar" ^
    --output "%DEX_DIR%" ^
    "%CLASSES_DIR%"
if errorlevel 1 goto :error

echo DEX OK

REM === Step 5: Package APK ===
echo.
echo --- Step 5: Package APK ---
"%AAPT2%" link -o "%BUILD_DIR%\%APP_NAME%-unsigned.apk" ^
    -I "%PLATFORM%\android.jar" ^
    --manifest "%PROJECT_DIR%app\src\main\AndroidManifest.xml" ^
    --proto-format ^
    "%BUILD_DIR%\res.zip"
if errorlevel 1 goto :error

rem Add classes.dex to APK
copy /y "%DEX_DIR%\classes.dex" "%BUILD_DIR%\classes.dex" >nul
"%AAPT2%" add "%BUILD_DIR%\%APP_NAME%-unsigned.apk" "%BUILD_DIR%\classes.dex" 2>nul
if errorlevel 1 (
    rem Fallback: use zip to add dex
    cd "%BUILD_DIR%"
    "%JAR%" uf "%APP_NAME%-unsigned.apk" classes.dex
    cd "%PROJECT_DIR%"
)

REM === Step 6: Sign APK (debug) ===
echo.
echo --- Step 6: Sign APK ---
rem Generate debug keystore if not exists
if not exist "%BUILD_DIR%\debug.keystore" (
    "%JAVA_HOME%\bin\keytool.exe" -genkey -v ^
        -keystore "%BUILD_DIR%\debug.keystore" ^
        -storepass android -alias androiddebugkey ^
        -keypass android -keyalg RSA -keysize 2048 -validity 10000 ^
        -dname "CN=Android Debug,O=Android,C=US" 2>nul
)

"%APKSIGNER%" sign --ks "%BUILD_DIR%\debug.keystore" ^
    --ks-pass pass:android --ks-key-alias androiddebugkey ^
    --key-pass pass:android ^
    --out "%BUILD_DIR%\%APP_NAME%.apk" ^
    "%BUILD_DIR%\%APP_NAME%-unsigned.apk"
if errorlevel 1 (
    REM If apksigner fails, try without it
    copy /y "%BUILD_DIR%\%APP_NAME%-unsigned.apk" "%BUILD_DIR%\%APP_NAME%.apk" >nul
    echo Warning: APK not signed (apksigner failed)
)

echo.
echo === Build complete ===
echo APK: %BUILD_DIR%\%APP_NAME%.apk
dir "%BUILD_DIR%\%APP_NAME%.apk"
goto :end

:error
echo.
echo === BUILD FAILED ===
exit /b 1

:end
