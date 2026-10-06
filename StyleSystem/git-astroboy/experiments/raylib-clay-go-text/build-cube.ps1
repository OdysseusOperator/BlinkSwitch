# Build script for the 3D Cube Experiment (Windows)

Write-Host "Building 3D Cube Experiment..." -ForegroundColor Cyan

Set-Location C:\dev\testOpencode\experiments\raylib-clay-go-example

# Build the cube experiment
go build -o cube-experiment.exe -ldflags="-s -w" cube-experiment.go

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful! Run cube-experiment.exe to start." -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
