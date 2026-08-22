@REM Maven Wrapper Script for Windows
@REM
@REM This script downloads and runs Maven if not already available.

@echo off
setlocal enabledelayedexpansion

set "MAVEN_VERSION=3.9.6"
set "MAVEN_HOME=%CD%\.mvn"

if not exist "%MAVEN_HOME%" (
    mkdir "%MAVEN_HOME%"
    echo Downloading Maven %MAVEN_VERSION%...
    powershell -Command "Invoke-WebRequest -Uri 'https://archive.apache.org/dist/maven/maven-3/%MAVEN_VERSION%/binaries/apache-maven-%MAVEN_VERSION%-bin.zip' -OutFile '%MAVEN_HOME%\maven.zip'; Expand-Archive -Path '%MAVEN_HOME%\maven.zip' -DestinationPath '%MAVEN_HOME%'; Move-Item '%MAVEN_HOME%\apache-maven-%MAVEN_VERSION%\*' '%MAVEN_HOME%' -Force; Remove-Item '%MAVEN_HOME%\apache-maven-%MAVEN_VERSION%', '%MAVEN_HOME%\maven.zip'"
)

call "%MAVEN_HOME%\bin\mvn.cmd" %*
