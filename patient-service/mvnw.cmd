@REM ----------------------------------------------------------------------------
@REM Maven Start Up Batch script
@REM Generated from Maven Wrapper (https://github.com/apache/maven-wrapper)
@REM ----------------------------------------------------------------------------
@setlocal

set MAVEN_HOME=%~dp0\.mvn\wrapper
set MAVEN_JAR=%MAVEN_HOME%\maven-wrapper.jar
set MAVEN_PROJECTBASEDIR=%~dp0

if not "%JAVA_HOME%" == "" goto javaHomeSet
set JAVA_HOME=C:\Program Files\Java\jdk-24
:javaHomeSet

"%JAVA_HOME%\bin\java.exe" %MAVEN_OPTS% "-Dmaven.multiModuleProjectDirectory=%MAVEN_PROJECTBASEDIR:~0,-1%" -cp "%MAVEN_JAR%" org.apache.maven.wrapper.MavenWrapperMain %*
if ERRORLEVEL 1 goto error
goto end

:error
exit /b 1

:end
@endlocal
