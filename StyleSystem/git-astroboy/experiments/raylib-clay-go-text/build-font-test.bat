@echo off
echo Building Monaspace Krypton Font Test...
go build -o font-test.exe main-clay.go
if %ERRORLEVEL% EQU 0 (
    echo Build successful! Run with: font-test.exe
) else (
    echo Build failed!
)
